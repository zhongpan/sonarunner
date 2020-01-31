#!/user/bin/env python
# -*- coding: UTF-8 -*-

import os
import subprocess
import datetime
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import argparse
from lxml import etree as ET
import os
import sys
import time
import math
from collections import OrderedDict
import ConfigParser
import StringIO
import shutil


class Util(object):
    @staticmethod
    def run_shell(cmd_line, out_file=None, env=None):
        out = subprocess.PIPE
        if out_file != None:
            out = out_file
        handle = subprocess.Popen(
            cmd_line, stdout=out, stderr=out, stdin=subprocess.PIPE, shell=True, env=env)
        return handle.wait()

    @staticmethod
    def run_shell_batch(cmd_infos, n, skip_failure, env=None, timeout_seconds=24*60*60):
        currents = []
        i = 0
        j = 0
        is_failure = False
        while i < len(cmd_infos) or len(currents) != 0:
            if is_failure and len(currents) == 0:
                return False
            while len(currents) < n and i < len(cmd_infos) and not is_failure:
                name, cmd_line, file_path = cmd_infos[i]
                file = open(file_path, "w")
                handle = subprocess.Popen(
                    cmd_line, stdout=file, stderr=file, stdin=subprocess.PIPE, shell=True, env=env)
                currents.append(
                    (name, cmd_line, file, handle, datetime.datetime.now()))
                i = i + 1
            for k in range(len(currents)-1, -1, -1):
                name, cmd_line, file, handle, start = currents[k]
                ret = handle.poll()
                if ret != None:
                    print "%d/%d" % (j + 1, len(cmd_infos)), cmd_line, ret
                    j = j + 1
                    file.close()
                    del currents[k]
                    if ret != 0 and not skip_failure:
                        is_failure = True
                else:
                    t = datetime.datetime.now() - start
                    if t.total_seconds() > timeout_seconds:
                        ret = -1
                        print "%d/%d" % (j + 1, len(cmd_infos)
                                         ), cmd_line, "timeout"
                        j = j + 1
                        handle.terminate()
                        file.close()
                        del currents[k]
                        if not skip_failure:
                            is_failure = True
        return True


# c++:community;cpp:commercial
LANG_CPP = "c++"
LANG_JAVA = "java"
LANG_JS = "javascript"


class Sln(object):
    def __init__(self, name, excludes, sonar_profile):
        self.projects = {}
        self.name = name
        self.excludes = excludes
        self.sonar_profile = sonar_profile

    def is_exclude(self, name):
        return len(filter(lambda x: name.find(x) >= 0, self.excludes)) > 0

    def get_sonar_profile(self):
        return self.sonar_profile


class Prj(object):
    def __init__(self, name, path):
        self.name = name
        self.real_name = name
        self.path = path

    def is_mvn(self):
        return False

    def get_src_base_dir(self):
        srcbasedir = os.path.abspath(self.path)
        if not os.path.isdir(srcbasedir):
            srcbasedir = os.path.dirname(self.path)
        return os.path.normpath(srcbasedir).replace("\\", "/")

    def get_src_dirs(self):
        return ['.']


vc_ns = 'http://schemas.microsoft.com/developer/msbuild/2003'


def get_vc_tag(tag):
    return "{%s}%s" % (vc_ns, tag)


class VCPrj(Prj):
    global_src_dirs = set()

    def __init__(self, name, real_name, path):
        Prj.__init__(self, name, path)
        self.real_name = real_name
        self.include_directories = []
        self.preprocessor_definitions = []
        self.src_dirs = set()
        self.src_base_dir = None

    def add_src_dir(self, src_dir, multi_include_samesrcdir):
        if src_dir in self.src_dirs:
            return
        if not multi_include_samesrcdir and src_dir in VCPrj.global_src_dirs:
            print "!warn:%s in %s already exists" % (src_dir, self.name)
            return
        VCPrj.global_src_dirs.add(src_dir)
        self.src_dirs.add(src_dir)

    def load(self, multi_include_samesrcdir):
        try:
            tree = ET.parse(self.path)
            if self.path.endswith(".vcxproj"):
                configuration_name = "Debug|x64"
                node = tree.find(".//%s[@Condition=\"'$(Configuration)|$(Platform)'=='%s'\"]/%s/%s" %
                                 (get_vc_tag('ItemDefinitionGroup'), configuration_name, get_vc_tag('ClCompile'), get_vc_tag('AdditionalIncludeDirectories')))
                self.include_directories = filter(
                    lambda x: not x.startswith('%('), node.text.split(";"))
                node = tree.find(".//%s[@Condition=\"'$(Configuration)|$(Platform)'=='%s'\"]/%s/%s" %
                                 (get_vc_tag('ItemDefinitionGroup'), configuration_name, get_vc_tag('ClCompile'), get_vc_tag('PreprocessorDefinitions')))
                self.preprocessor_definitions = filter(
                    lambda x: not x.startswith('%('), node.text.split(";"))
                nodes = tree.findall(
                    ".//%s/%s" % (get_vc_tag('ItemGroup'), get_vc_tag('ClInclude')))
                for node in nodes:
                    self.add_src_dir(os.path.dirname(
                        node.get("Include")), multi_include_samesrcdir)
                nodes = tree.findall(
                    ".//%s/%s" % (get_vc_tag('ItemGroup'), get_vc_tag('ClCompile')))
                for node in nodes:
                    self.add_src_dir(os.path.dirname(
                        node.get("Include")), multi_include_samesrcdir)
            else:
                configuration_name = "Debug|Win32"
                node = tree.find(
                    ".//Configuration[@Name='%s']/Tool[@Name='VCCLCompilerTool']" % configuration_name)
                self.include_directories = node.get(
                    "AdditionalIncludeDirectories").split(";")
                self.preprocessor_definitions = node.get(
                    "PreprocessorDefinitions").split(";")
                nodes = tree.findall(".//Files//File")
                for node in nodes:
                    self.add_src_dir(os.path.dirname(
                        node.get("RelativePath")), multi_include_samesrcdir)
            if len(self.src_dirs) > 0:
                self.src_base_dir = os.path.commonprefix(self.src_dirs)
        except Exception, e:
            print e
            return False
        return True

    def get_src_base_dir(self):
        if len(self.src_dirs) == 0:
            return super(VCPrj, self).get_src_base_dir()
        return os.path.normpath(self.src_base_dir).replace("\\", "/")

    def get_src_dirs(self):
        rel_src_dirs = set()
        for src_dir in self.src_dirs:
            rel_src_dir = os.path.relpath(src_dir, self.src_base_dir)
            if rel_src_dir == '':
                rel_src_dir = '.'
            rel_src_dirs.add(rel_src_dir.replace("\\", "/"))
        sub_dirs = set()
        for rel_src_dir in rel_src_dirs:
            for other in rel_src_dirs:
                if rel_src_dir == other:
                    continue
                if not os.path.relpath(rel_src_dir, other).startswith(".."):
                    sub_dirs.add(rel_src_dir)
        rel_src_dirs = filter(lambda x: x not in sub_dirs, rel_src_dirs)
        return rel_src_dirs if len(rel_src_dirs) > 0 else ['.']


class VCSln(Sln):
    def __init__(self, base_dir, name, excludes, sonar_profile):
        Sln.__init__(self, name, excludes, sonar_profile)
        self.depend_projects = []
        self.base_dir = base_dir

    def load(self, file_path, multi_include_samesrcdir):
        self.path = file_path
        file = open(file_path)
        try:
            lines = file.readlines()
            id = ""
            for line in lines:
                if line.startswith('Project("{'):
                    name, path, id = map(lambda x: x.strip()[
                                         1:-1], line.split(" = ")[1].split(", "))
                    if name == "ALL_BUILD" or name == "ZERO_CHECK":
                        continue
                    if path.startswith(".."):
                        self.depend_projects.append(name)
                    else:
                        real_name = name
                        if self.is_exclude(real_name):
                            continue
                        project = VCPrj(name, real_name, os.path.join(
                            os.path.dirname(file_path), path))
                        if not project.load(multi_include_samesrcdir):
                            return False
                        self.projects[id] = project
        except Exception, e:
            print e
            return False
        finally:
            file.close()
        return True

    def get_language(self):
        return LANG_CPP

    def get_encode(self):
        return "GBK"


class NBPrj(Prj):
    def __init__(self, name, path):
        Prj.__init__(self, name, path)


class NBSln(Sln):
    def __init__(self, name, excludes, sonar_profile):
        Sln.__init__(self, name, excludes, sonar_profile)

    def load(self, path):
        self.path = path
        try:
            cf = ConfigParser.ConfigParser()
            cfg_str = '[root]\n' + open(path, 'r').read()
            cfg_fp = StringIO.StringIO(cfg_str)
            cf.readfp(cfg_fp)
            for opt in cf.options('root'):
                if opt.startswith('project.'):
                    name = cf.get('root', opt)
                    project_dir = "."
                    if name.find('/') >= 0:
                        project_dir = os.path.dirname(name)
                        name = os.path.basename(name)
                    if self.is_exclude(name):
                        continue
                    project = NBPrj(name, os.path.join(
                        os.path.dirname(path), "..", project_dir, name))
                    self.projects[opt] = project
        except Exception, e:
            print e
            return False
        return True

    def get_language(self):
        return LANG_JAVA

    def get_encode(self):
        return "UTF-8"


class MvnProj(Prj):
    def __init__(self, name, path):
        Prj.__init__(self, name, path)

    def is_mvn(self):
        return True


pom_ns = 'http://maven.apache.org/POM/4.0.0'


def get_pom_tag(tag):
    return "{%s}%s" % (pom_ns, tag)


class MvnSln(Sln):
    def __init__(self, name, excludes, sonar_profile):
        Sln.__init__(self, name, excludes, sonar_profile)

    def do_load(self, path):
        try:
            if not os.path.exists(path):
                print "!warn:%s not exists" % path
                return True
            tree = ET.parse(path)
            nodes = tree.findall(".//%s/%s" %
                                 (get_pom_tag('modules'), get_pom_tag('module')))
            if len(nodes) == 0:
                id = tree.find("./%s" % get_pom_tag("artifactId"))
                self.projects[id.text] = MvnProj(id.text, path)
                return True
            for node in nodes:
                if not self.do_load(os.path.join(
                        os.path.dirname(path), node.text, "pom.xml")):
                    return False
        except Exception, e:
            print e
            return False
        return True

    def load(self, path):
        self.path = path
        return self.do_load(self.path)


class Timer(object):
    def __init__(self):
        self.start = datetime.datetime.now()

    def elapse(self, name):
        d = datetime.datetime.now()
        if not hasattr(self, "last"):
            self.last = self.start
        print "%s: %s/%s" % (name, str(datetime.datetime(1970, 1, 1, 0, 0, 0, 0) + (d - self.last))[11:],
                             str(datetime.datetime(1970, 1, 1, 0, 0, 0, 0) + (d - self.start))[11:])
        self.last = d


class System(object):
    def __init__(self, version, name):
        self.sonar_projects = []
        self.version = version
        self.name = name

    def add_sonar_project(self, sonarprj):
        self.sonar_projects.append(sonarprj)

    @staticmethod
    def get_work_dir(name, version):
        return "%s-%s" % (name, version)

    def run_sonar_scanner(self, n, dry_run, filters, skip_failure):
        cmd_infos = []
        for project in self.sonar_projects:
            cmd_infos.append(project.get_cmd_line(
                self.name, self.version, self.temp_dir))
        if filters:
            cmd_infos = filter(lambda x: len(
                filter(lambda y: x[0].find(y) >= 0, filters)) > 0, cmd_infos)
        ret = True
        if dry_run:
            i = 1
            for cmdinfo in cmd_infos:
                print "%d/%d %s" % (i, len(cmd_infos), cmdinfo[1])
                i = i + 1
        else:
            if not Util.run_shell_batch(cmd_infos, n, skip_failure):
                return False
            # remove from sonarqube 7.1
            #cmdline_view = "sonar-scanner views"
            #file_view = open(os.path.join(self.tempdir, "sonar_scanner_views.out"), "w")
            # try:
            #    print cmdline_view, Util.runshell(cmdline_view, file_view, env)
            # except Exception, e:
            #    ret = False
            # finally:
            #    file_view.close()
        return ret

    def run(self, n, dry_run, filters, skip_failure):
        self.work_dir = System.get_work_dir(self.name, self.version)
        if not os.path.exists(self.work_dir):
            os.mkdir(self.work_dir)
        self.temp_dir = os.path.join(self.work_dir, "temp")
        if not os.path.exists(self.temp_dir):
            os.mkdir(self.temp_dir)
        return self.run_sonar_scanner(n, dry_run, filters, skip_failure)


class SonarPrj(object):
    def __init__(self, sln, project):
        self.sln = sln
        self.project = project

    def gen_sonar_project_file(self, name, version):
        properties = "sonar.projectKey=%s_%s:%s:%s\n" % (
            name, version, self.sln.name, self.project.name)
        properties += "sonar.projectName=%s\n" % self.project.name
        properties += "sonar.projectVersion=%s\n" % version
        properties += "sonar.sourceEncoding=%s\n" % self.sln.get_encode()
        properties += "sonar.language=%s\n" % self.sln.get_language()
        properties += "sonar.profile=%s\n" % self.sln.get_sonar_profile()
        properties += "sonar.working.directory=%s/.sonar_%s\n" % (
            System.get_work_dir(name, version), self.project.name)
        properties += "sonar.sources=%s\n" % ','.join(
            self.project.get_src_dirs())
        properties += "sonar.projectBaseDir=%s\n" % self.project.get_src_base_dir()
        if self.sln.get_language() == LANG_CPP:
            properties += "sonar.cxx.defines=%s\n" % " \\n\\ ".join(
                self.project.preprocessor_definitions)
            properties += "sonar.cxx.includeDirectories=%s\n" % ",".join(
                self.project.include_directories).replace("\\", "/")
            properties += "sonar.cfamily.build-wrapper-output.bypass=true\n"
            properties += "sonar.exclusions=**/*.java\n"
        elif self.sln.get_language() == LANG_JAVA:
            properties += "sonar.java.binaries=%s\n" % "build/classes"
        self.path = os.path.join(System.get_work_dir(
            name, version), "%s.properties" % self.project.name)
        file = open(self.path, "w")
        file.write(properties)
        file.close()

    def get_cmd_line(self, name, version, temp_dir):
        if not self.project.is_mvn():
            self.gen_sonar_project_file(name, version)
            cmd_line = "sonar-scanner -Dproject.settings=%s" % self.path
            return (self.project.name, cmd_line, os.path.join(temp_dir, "sonar_scanner_%s.out" % self.project.name))
        else:
            cmd_line = "mvn clean compile sonar:sonar -f %s -Dsonar.profile=%s -Dmaven.test.failure.ignore=true" % (
                self.project.path, self.sln.get_sonar_profile())
            return (self.project.name, cmd_line, os.path.join(temp_dir, "sonar_mvn_%s.out" % self.project.name))


class SonarRunner(object):
    def __init__(self):
        self.systems = []

    def load_project(self, system, name, project_base_dir, project_dir, project_file,
                 excludes, sonar_profile, multi_include_samesrcdir):
        if excludes:
            excludes = excludes.split(",")
        else:
            excludes = []
        sln = None
        base_dir = os.path.join(project_base_dir, project_dir)
        sln_path = os.path.join(base_dir, project_file)
        if project_file.endswith(".sln"):
            sln = VCSln(base_dir, name, excludes, sonar_profile)
            if not sln.load(sln_path, multi_include_samesrcdir):
                return False
        elif project_file.endswith(".properties"):
            sln = NBSln(name, excludes, sonar_profile)
            if not sln.load(sln_path):
                return False
        elif project_file.endswith("pom.xml"):
            sln = MvnSln(name, excludes, sonar_profile)
            if not sln.load(sln_path):
                return False
        if not sln:
            return False
        for project in sln.projects.values():
            sonar_prject = SonarPrj(sln, project)
            system.add_sonar_project(sonar_prject)
        return True

    def load_config(self, src_path, config_path, sonar_profile, multi_include_samesrcdir):
        try:
            tree = ET.parse(config_path)
            for node in tree.findall(".//system"):
                base_dir = os.path.join(
                    src_path, node.get("relative-path"))
                system_name = node.get("name")
                system_version = node.get("version")
                system = System(system_version, system_name)
                self.systems.append(system)
                for subsystem in node.findall("./subsystem"):
                    project_dir = subsystem.get("relative-path")
                    subsys_name = subsystem.get("name")
                    for project in subsystem.findall("./project"):
                        project_file = project.get("file")
                        project_name = project.get("name")
                        if project_name:
                            project_name = "_".join([subsys_name, project_name])
                        else:
                            project_name = subsys_name
                        if not self.load_project(system, project_name, base_dir,
                                             project_dir, project_file, project.get("excludes"), sonar_profile, multi_include_samesrcdir):
                            return False
        except Exception, e:
            print e
            return False
        return True

    def run(self, n, dryrun, filters, skip_failure):
        t = Timer()
        for system in self.systems:
            if not system.run(n, dryrun, filters, skip_failure):
                return False
            t.elapse("%s" % system.name)
        return True


def main(src_path, config_file, sonar_profile, n, dry_run, filters, skip_failure, multi_include_samesrcdir):
    s = SonarRunner()
    if not s.load_config(src_path, config_file, sonar_profile, multi_include_samesrcdir):
        return False
    return s.run(n, dry_run, filters, skip_failure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='cmd options')
    parser.add_argument(
        "--config", "-c", help="project configuration file", type=str, default="sonar.conf")
    parser.add_argument("--sonar_profile", "-p",
                        help="sonar quality profile", type=str, default="unm")
    parser.add_argument(
        "--jobs", "-j", help="max sonar scanner job count", type=int, default=3)
    parser.add_argument("--dry_run", "-dr", help="dry run",
                        action="store_true", default=False)
    parser.add_argument(
        "--filter", "-f", help="filter list", type=str, nargs="+")
    parser.add_argument("--skip_failure", "-sf",
                        help="skip failure", action="store_true", default=False)
    parser.add_argument("--multi_include_samesrcdir", "-m",
                        help="multi_include_samesrcdir", action="store_true", default=False)
    parser.add_argument("path", help="source code root dir",
                        type=str, default=".")
    args = parser.parse_args()
    ret = main(args.path, args.config, args.sonar_profile, args.jobs, args.dry_run,
                args.filter, args.skip_failure, args.multi_include_samesrcdir)
    exit(0 if ret else 1)
