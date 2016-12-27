#!/user/bin/python
# -*- coding: UTF-8 -*-

import os,subprocess,datetime
try: 
  import xml.etree.cElementTree as ET 
except ImportError: 
  import xml.etree.ElementTree as ET
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import argparse

class Util(object):
    @staticmethod
    def runshell(cmdline, outfile=None, env=None): 
        out = subprocess.PIPE
        if outfile != None:
            out = outfile
        handle = subprocess.Popen(cmdline, stdout=out, stderr=out, stdin=subprocess.PIPE, shell=True, env=env) 
        return handle.wait() 
    
    @staticmethod
    def runshellbatch(cmdinfos, n):
        pass
        
configurationname = "Debug|Win32"
    
class VCPrj(object):
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.includedirectories = []
        self.preprocessordefinitions = []
        
    def load(self):
        try: 
            tree = ET.parse(self.path)
            root = tree.getroot()
            node = tree.find(".//Configuration[@Name='%s']/Tool[@Name='VCCLCompilerTool']" % configurationname)
            self.includedirectories = node.get("AdditionalIncludeDirectories").split(";")
            self.preprocessordefinitions = node.get("PreprocessorDefinitions").split(";")
        except Exception, e:
            print e
            return False
        return True
        
        
class VCSln(object):
    def __init__(self):
        self.projects = {}
        self.dependprojects = []
        
    def load(self, filepath):
        self.path = filepath
        file = open(filepath)
        try:
            lines = file.readlines()
            id = ""
            for line in lines:
                if line.startswith('Project("{'):
                    name, path, id = map(lambda x:x.strip()[1:-1], line.split(" = ")[1].split(", "))
                    if name == "ALL_BUILD" or name == "ZERO_CHECK":
                        continue
                    if path.startswith(".."):
                        self.dependprojects.append(name)
                    else:
                        if name.endswith("_stlp") or name.endswith("_stlpd"):
                            name = name[0:name.rindex('_')]
                        project = VCPrj(name, os.path.join(os.path.dirname(filepath), path))
                        if not project.load():
                            return False
                        self.projects[id] = project
        except Exception, e:
            print e
            return False
        finally:
            file.close()
        return True
        
    def getpclintcmd(self, productdir, name, excludes):
        depends = self.dependprojects + excludes
        cmdline = 'VisualLintConsole %s /config="%s" /excludeproject="%s" /exportfile="%s" /exportformat=%s' % \
        (self.path, configurationname, ",".join(depends), os.path.join(productdir, "%s_pclint.xml" % name), "SonarEnvXml.txt")
        return cmdline
        
    def getprjname(self):
        return filter(lambda x:"test_" not in x, map(lambda x:x.name, self.projects.values()))

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
        
class Product(object):
    def __init__(self, version, name, dir):
        self.sonarprjs = []
        self.version = version
        self.name = name
        self.dir = dir
        
    def addSonarPrj(self, sonarprj):
        self.sonarprjs.append(sonarprj)
    
    @staticmethod
    def getProductDir(productname, productver):
        return "%s-%s" % (productname, productver)
        
    def runupdatesvn(self):
        cmdline = "svn update %s" % self.dir
        file = open(os.path.join(self.tempdir, "svn.out"), "w")
        try:
            print cmdline, Util.runshell(cmdline, file)
        finally:
            file.close()
        
    def runcmake(self):
        cmdline = os.path.join(self.dir, "Build/cmake_create_all_unm_stlp_makes.bat")
        env = os.environ
        env["UNM_NO_PAUSE"] = "1"
        file = open(os.path.join(self.tempdir, "cmake.out"), "w")
        try:
            print cmdline, Util.runshell(cmdline, file, env)
        finally:
            file.close()
        
    def runpclint(self):
        for i in range(len(self.sonarprjs)):
            sonarprj = self.sonarprjs[i]
            cmdline = sonarprj.getpclintcmd(self.productdir)
            file = open(os.path.join(self.tempdir, "pclint_%s.out" % sonarprj.name), "w")
            try:
                print "%d/%d" % (i+1, len(self.sonarprjs)), cmdline, Util.runshell(cmdline, file)
            finally:
                file.close()

    def runsonar(self):
        for i in range(len(self.sonarprjs)):
            sonarprj = self.sonarprjs[i]
            sonarprj.genprjfile(self.name, self.version)
            cmdline = "sonar-scanner -Dproject.settings=%s" % sonarprj.prjfilepath
            file = open(os.path.join(self.tempdir, "sonar_scanner_%s.out" % sonarprj.name), "w")
            env = os.environ
            env["SONAR_SCANNER_OPTS"] = "-Xmx1024m"
            try:
                print "%d/%d" % (i+1, len(self.sonarprjs)), cmdline, Util.runshell(cmdline, file, env)
            finally:
                file.close()                
            
    def run(self):
        t = Timer()
        self.productdir = Product.getProductDir(self.name, self.version)
        if not os.path.exists(self.productdir):
            os.mkdir(self.productdir)
        self.tempdir = os.path.join(self.productdir, "temp")
        if not os.path.exists(self.tempdir):
            os.mkdir(self.tempdir)      
        self.runupdatesvn()
        t.elapse("step1")
        self.runcmake()
        t.elapse("step2")
        self.runpclint()
        t.elapse("step3")
        self.runsonar()
        t.elapse("step4")
        
    def printtimeelapse(self, name):
        self.thisstep = datetime.datetime.now()
        d = datetime.datetime.now() - self.start
        print "%s: %s" % (name, str(datetime.datetime(1970, 1, 1, 0, 0, 0, 0) + d)[11:])
        
class SonarPrj(object):
    def __init__(self, subsysname, name, srcdir, vcsln, excludes):
        self.subsysname = subsysname
        self.name = name
        self.srcdir = srcdir
        self.vcsln = vcsln
        self.excludes = excludes
    
    def getpclintcmd(self, productdir):
        return self.vcsln.getpclintcmd(productdir, self.name, self.excludes)
        
    def genprjfile(self, productname, productver):
        prjproperties = "sonar.projectKey=%s:%s:%s\n" % (productname, self.subsysname, self.name)
        prjproperties += "sonar.projectName=%s\n" % self.name
        prjproperties += "sonar.projectVersion=%s\n" % productver
        prjproperties += "sonar.sourceEncoding=GBK\n"
        prjproperties += "sonar.language=c++\n"
        prjproperties += "sonar.profile=pclint\n"
        prjproperties += "sonar.working.directory=%s/.sonar_%s\n" % (Product.getProductDir(productname, productver), self.name)
        prjproperties += "sonar.cxx.pclint.reportPath=%s\n" % os.path.abspath(os.path.join(Product.getProductDir(productname, productver), "%s_pclint.xml" % self.name)).replace("\\", "/")
        prjproperties += "sonar.modules=%s\n" % ",".join(map(lambda x:x.name, self.vcsln.projects.values()))
        for module in self.vcsln.projects.values():
            prjproperties += "%s.sonar.projectName=%s\n" % (module.name, module.name)
            prjproperties += "%s.sonar.projectBaseDir=%s\n" % (module.name, os.path.dirname(module.path).replace(os.path.dirname(self.vcsln.path), self.srcdir).replace("\\", "/"))
            prjproperties += "%s.sonar.sources=.\n" % module.name
            prjproperties += "%s.sonar.cxx.defines=%s\n" % (module.name, " \\n\\ ".join(module.preprocessordefinitions))
            prjproperties += "%s.sonar.cxx.includeDirectories=%s\n" % (module.name, ",".join(module.includedirectories).replace("\\", "/"))
        self.prjfilepath = os.path.join(Product.getProductDir(productname, productver), "%s.properties" % self.name)
        file = open(self.prjfilepath, "w")
        file.write(prjproperties)
        file.close()
        
class SonarMgr(object):
    def __init__(self):
        self.products = []
    def loadConf(self, path):
        try: 
            tree = ET.parse(path)
            for node in tree.findall(".//product"):
                product = Product(node.get("version"), node.get("name"), node.get("srcbasedir"))
                self.products.append(product)
                for subsystem in node.findall("./subsystem"):
                    for project in subsystem.findall("./project"):
                        vcslnpath = os.path.join(node.get("projectbasedir"), 
                        subsystem.get("projectdir"), project.get("file"))
                        srcdir = os.path.dirname(os.path.join(node.get("srcbasedir"), 
                        subsystem.get("srcdir"), project.get("file")))
                        excludes = []
                        if project.get("exclude"):
                            excludes = project.get("exclude").split(",")
                        vcsln = VCSln()
                        if not vcsln.load(vcslnpath):
                            return False
                        sonarprj = SonarPrj(subsystem.get("name"), project.get("name"), srcdir, vcsln, excludes)
                        product.addSonarPrj(sonarprj)
        except Exception, e:
            print e
            return False
        return True 
    def run(self):
        for product in self.products:
            product.run()
    
def sonar_job(path):
    s = SonarMgr()
    if s.loadConf(path):
        s.run()
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='cmd options')
    parser.add_argument("-rs", "--runsonar", help="run sonar", default="sonar.conf")
    parser.add_argument("-lm", "--listmodule", help="list module", action="store_true")
    args = parser.parse_args()
    if args.runsonar:
        i = raw_input("run immediately(y,default) or periodic(n):")
        if i == "" or i == "y":
           sonar_job(args.runsonar)
        else:
           trig = CronTrigger(second=0, minute=0, hour=18, day_of_week='2,6') # 周三，周日
           print trig
           schedudler = BlockingScheduler()
           schedudler.add_job(sonar_job, trig, [args.runsonar])
           schedudler.start()
    elif args.listmodule:
        sln = VCSln()
        sln.load("D:\\u2k_dev_trunk\\s\\tmp\\cmake_stlp\\platform\\AllProjects_UnmPlatform.sln")
        result = sln.getprjname()
        print "\n".join(result)
        print len(result)
    
