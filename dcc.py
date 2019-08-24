#!/usr/bin/env python
# coding=utf-8
import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile

from androguard.core import androconf
from androguard.core.analysis import analysis
from androguard.core.androconf import show_logging
from androguard.core.bytecodes import apk, dvm
from androguard.util import read
from dex2c.compiler import Dex2C
from dex2c.util import JniLongName, get_method_triple, get_access_method, is_synthetic_method, is_native_method

APKTOOL = 'tools/apktool.jar'
SIGNJAR = 'tools/signapk.jar'
LIBNATIVECODE = 'libnc.so'

logger = logging.getLogger('dcc')

tempfiles = []


def make_temp_dir(prefix='dcc'):
    global tempfiles
    tmp = tempfile.mkdtemp(prefix=prefix)
    tempfiles.append(tmp)
    return tmp


def make_temp_file(suffix=''):
    global tempfiles
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    tempfiles.append(tmp)
    return tmp


def clean_temp_files():
    for name in tempfiles:
        if not os.path.exists(name):
            continue
        logger.info('removing %s' % name)
        if os.path.isdir(name):
            shutil.rmtree(name)
        else:
            os.unlink(name)


class ApkTool(object):
    @staticmethod
    def decompile(apk):
        outdir = make_temp_dir('dcc-apktool-')
        subprocess.check_call(['java', '-jar', APKTOOL, 'd', '-r', '-f', '-o', outdir, apk])
        return outdir

    @staticmethod
    def compile(decompiled_dir):
        unsiged_apk = make_temp_file('-unsigned.apk')
        subprocess.check_call(['java', '-jar', APKTOOL, 'b', '-o', unsiged_apk, decompiled_dir])
        return unsiged_apk


def sign(unsigned_apk, signed_apk):
    pem = os.path.join('tests/testkey/testkey.x509.pem')
    pk8 = os.path.join('tests/testkey/testkey.pk8')
    subprocess.check_call(['java', '-jar', SIGNJAR, pem, pk8, unsigned_apk, signed_apk])


def build_project(project_dir):
    subprocess.check_call(['ndk-build', '-j8', '-C', project_dir])


def auto_vm(filename):
    ret = androconf.is_android(filename)
    if ret == 'APK':
        return dvm.DalvikVMFormat(apk.APK(filename).get_dex())
    elif ret == 'DEX':
        return dvm.DalvikVMFormat(read(filename))
    elif ret == 'DEY':
        return dvm.DalvikOdexVMFormat(read(filename))
    raise Exception("unsupported file %s" % filename)


class MethodFilter(object):
    def __init__(self, configure, vm):
        self._compile_filters = []
        self._keep_filters = []
        self._compile_full_match = set()

        self.conflict_methods = set()
        self.native_methods = set()
        self.annotated_methods = set()

        self._load_filter_configure(configure)
        self._init_conflict_methods(vm)
        self._init_native_methods(vm)
        self._init_annotation_methods(vm)

    def _load_filter_configure(self, configure):
        if not os.path.exists(configure):
            return

        with open(configure) as fp:
            for line in fp:
                line = line.strip()
                if not line or line[0] == '#':
                    continue

                if line[0] == '!':
                    line = line[1:].strip()
                    self._keep_filters.append(re.compile(line))
                elif line[0] == '=':
                    line = line[1:].strip()
                    self._compile_full_match.add(line)
                else:
                    self._compile_filters.append(re.compile(line))

    def _init_conflict_methods(self, vm):
        all_methods = {}
        for m in vm.get_methods():
            method_triple = get_method_triple(m, return_type=False)
            if method_triple in all_methods:
                self.conflict_methods.add(m)
                self.conflict_methods.add(all_methods[method_triple])
            else:
                all_methods[method_triple] = m

    def _init_native_methods(self, vm):
        for m in vm.get_methods():
            cls_name, name, _ = get_method_triple(m)

            access = get_access_method(m.get_access_flags())
            if 'native' in access:
                self.native_methods.add((cls_name, name))

    def _add_annotation_method(self, method):
        if not is_synthetic_method(method) and not is_native_method(method):
            self.annotated_methods.add(method)

    def _init_annotation_methods(self, vm):
        for c in vm.get_classes():
            adi_off = c.get_annotations_off()
            if adi_off == 0:
                continue

            adi = vm.CM.get_obj_by_offset(adi_off)
            annotated_class = False
            # ref:https://github.com/androguard/androguard/issues/175
            if adi.get_class_annotations_off() != 0:
                ann_set_item = vm.CM.get_obj_by_offset(adi.get_class_annotations_off())
                for aoffitem in ann_set_item.get_annotation_off_item():
                    annotation_item = vm.CM.get_obj_by_offset(aoffitem.get_annotation_off())
                    encoded_annotation = annotation_item.get_annotation()
                    type_desc = vm.CM.get_type(encoded_annotation.get_type_idx())
                    if type_desc.endswith('Dex2C;'):
                        annotated_class = True
                        for method in c.get_methods():
                            self._add_annotation_method(method)
                        break

            if not annotated_class:
                for mi in adi.get_method_annotations():
                    method = vm.get_method_by_idx(mi.get_method_idx())
                    ann_set_item = vm.CM.get_obj_by_offset(mi.get_annotations_off())

                    for aoffitem in ann_set_item.get_annotation_off_item():
                        annotation_item = vm.CM.get_obj_by_offset(aoffitem.get_annotation_off())
                        encoded_annotation = annotation_item.get_annotation()
                        type_desc = vm.CM.get_type(encoded_annotation.get_type_idx())
                        if type_desc.endswith('Dex2C;'):
                            self._add_annotation_method(method)

    def should_compile(self, method):
        # don't compile functions that have same parameter but differ return type
        if method in self.conflict_methods:
            return False

        # synthetic method
        if is_synthetic_method(method) or is_native_method(method):
            return False

        method_triple = get_method_triple(method)
        cls_name, name, _ = method_triple

        # Android VM may find the wrong method using short jni name
        # don't compile function if there is a same named native method
        if (cls_name, name) in self.native_methods:
            return False

        full_name = ''.join(method_triple)
        for rule in self._keep_filters:
            if rule.search(full_name):
                return False

        if full_name in self._compile_full_match:
            return True

        if method in self.annotated_methods:
            return True

        for rule in self._compile_filters:
            if rule.search(full_name):
                return True

        return False


def copy_compiled_libs(project_dir, decompiled_dir):
    compiled_libs_dir = os.path.join(project_dir, "libs")
    decompiled_libs_dir = os.path.join(decompiled_dir, "lib")
    if not os.path.exists(compiled_libs_dir):
        return
    if not os.path.exists(decompiled_libs_dir):
        shutil.copytree(compiled_libs_dir, decompiled_libs_dir)
        return

    for abi in os.listdir(decompiled_libs_dir):
        dst = os.path.join(decompiled_libs_dir, abi)
        src = os.path.join(compiled_libs_dir, abi)
        if not os.path.exists(src) and abi == 'armeabi':
            src = os.path.join(compiled_libs_dir, 'armeabi-v7a')
            logger.warning('Use armeabi-v7a for armeabi')

        if not os.path.exists(src):
            raise Exception("ABI %s is not supported!" % abi)

        libnc = os.path.join(src, LIBNATIVECODE)
        shutil.copy(libnc, dst)


def native_class_methods(smali_path, compiled_methods):
    def _skip_until(fp, needle):
        while True:
            line = fp.readline()
            if not line:
                break
            if line.strip() == needle:
                break

    code_lines = []
    class_name = ''
    with open(smali_path, 'r') as fp:
        while True:
            line = fp.readline()
            if not line:
                break
            code_lines.append(line)
            line = line.strip()
            if line.startswith('.class'):
                class_name = line.split(' ')[-1]
            elif line.startswith('.method'):
                current_method = line.split(' ')[-1]
                param = current_method.find('(')
                name, proto = current_method[:param], current_method[param:]
                if (class_name, name, proto) in compiled_methods:
                    code_lines[-1] = code_lines[-1].replace(current_method, 'native ' + current_method)
                    _skip_until(fp, '.end method')
                    code_lines.append('.end method\n')

    with open(smali_path, 'w') as fp:
        fp.writelines(code_lines)


def native_compiled_dexes(decompiled_dir, compiled_methods):
    # smali smali_classes2 smali_classes3 ...
    classes_output = list(filter(lambda x: x.find('smali') >= 0, os.listdir(decompiled_dir)))
    todo = []
    for classes in classes_output:
        for method_triple in compiled_methods.keys():
            cls_name, name, proto = method_triple
            cls_name = cls_name[1:-1]  # strip L;
            smali_path = os.path.join(decompiled_dir, classes, cls_name) + '.smali'
            if os.path.exists(smali_path):
                todo.append(smali_path)

    for smali_path in todo:
        native_class_methods(smali_path, compiled_methods)


def write_compiled_methods(project_dir, compiled_methods):
    source_dir = os.path.join(project_dir, 'jni', 'nc')
    if not os.path.exists(source_dir):
        os.makedirs(source_dir)

    for method_triple, code in compiled_methods.items():
        full_name = JniLongName(*method_triple)
        filepath = os.path.join(source_dir, full_name) + '.cpp'
        if os.path.exists(filepath):
            logger.warning("Overwrite file %s %s" % (filepath, method_triple))

        with open(filepath, 'w') as fp:
            fp.write('#include "Dex2C.h"\n' + code)

    with open(os.path.join(source_dir, 'compiled_methods.txt'), 'w') as fp:
        fp.write('\n'.join(list(map(''.join, compiled_methods.keys()))))


def archive_compiled_code(project_dir):
    outfile = make_temp_file('-dcc')
    outfile = shutil.make_archive(outfile, 'zip', project_dir)
    return outfile


def compile_dex(apkfile, filtercfg):
    show_logging(level=logging.INFO)

    d = auto_vm(apkfile)
    dx = analysis.Analysis(d)

    method_filter = MethodFilter(filtercfg, d)

    compiler = Dex2C(d, dx)

    compiled_method_code = {}
    errors = []

    for m in d.get_methods():
        method_triple = get_method_triple(m)

        jni_longname = JniLongName(*method_triple)
        full_name = ''.join(method_triple)

        if len(jni_longname) > 220:
            logger.debug("name to long %s(> 220) %s" % (jni_longname, full_name))
            continue

        if method_filter.should_compile(m):
            logger.debug("compiling %s" % (full_name))
            try:
                code = compiler.get_source_method(m)
            except Exception as e:
                logger.warning("compile method failed:%s (%s)" % (full_name, str(e)), exc_info=True)
                errors.append('%s:%s' % (full_name, str(e)))
                continue

            if code:
                compiled_method_code[method_triple] = code

    return compiled_method_code, errors


def is_apk(name):
    return name.endswith('.apk')


def dcc(apkfile, filtercfg, outapk, do_compile=True, project_dir=None, source_archive='project-source.zip'):
    if not os.path.exists(apkfile):
        logger.error("file %s is not exists", apkfile)
        return

    compiled_methods, errors = compile_dex(apkfile, filtercfg)

    if errors:
        logger.warning('================================')
        logger.warning('\n'.join(errors))
        logger.warning('================================')

    if len(compiled_methods) == 0:
        logger.info("no compiled methods")
        return

    if project_dir:
        write_compiled_methods(project_dir, compiled_methods)
    else:
        project_dir = make_temp_dir('dcc-project-')
        shutil.rmtree(project_dir)
        shutil.copytree('project', project_dir)
        write_compiled_methods(project_dir, compiled_methods)
        src_zip = archive_compiled_code(project_dir)
        shutil.move(src_zip, source_archive)

    if do_compile:
        build_project(project_dir)

    if is_apk(apkfile) and outapk:
        decompiled_dir = ApkTool.decompile(apkfile)
        native_compiled_dexes(decompiled_dir, compiled_methods)
        copy_compiled_libs(project_dir, decompiled_dir)
        unsigned_apk = ApkTool.compile(decompiled_dir)
        sign(unsigned_apk, outapk)


sys.setrecursionlimit(5000)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('infile', help='Input APK,DEX name')
    parser.add_argument('-o', '--out', nargs='?', help='Output APK file name')
    parser.add_argument('--sign', action='store_true', default=False, help='Sign apk')
    parser.add_argument('--filter', default='filter.txt', help='Method filter configure file')
    parser.add_argument('--no-build', action='store_true', default=False, help='Do not build the compiled code')
    parser.add_argument('--source-dir', help='The compiled cpp code output directory.')
    parser.add_argument('--project-archive', default='project-source.zip', help='Archive the project directory')

    args = vars(parser.parse_args())
    infile = args['infile']
    outapk = args['out']
    do_sign = args['sign']
    filtercfg = args['filter']
    do_compile = not args['no_build']
    source_archive = args['project_archive']

    if args['source_dir']:
        project_dir = args['source_dir']
    else:
        project_dir = None

    try:
        dcc(infile, filtercfg, outapk, do_compile, project_dir, source_archive)
    except Exception as e:
        logger.error("Compile %s failed!" % infile, exc_info=True)
    finally:
        clean_temp_files()

