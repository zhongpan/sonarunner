# sonarunner
sonarrunner用于从各种IDE工程执行sonar检查，解决如下问题：
* 自动生成sonar工程文件，解决手写不不便，例如C++工程，需要头文件路径和宏定义写在工程文件中；
* 增加并发执行，解决大量工程检查慢问题；
* 通过配置文件重新组织工程，便于在soanr中检索和聚合。

# 支持的IDE工程类型
* VC工程，包括vcproj和vcxproj
* Netbeans RCP工程
* mvn工程

# 使用前提
* 安装好sonar-scanner
* 如mvn工程，需安装好mvn

# 使用方法
```
$ python sonarunner.py --help                                                 
usage: sonarunner.py [-h] [--config CONFIG] [--sonar_profile SONAR_PROFILE]   
                     [--jobs JOBS] [--dry_run] [--filter FILTER [FILTER ...]] 
                     [--skip_failure] [--multi_include_samesrcdir]            
                     path                                                     
                                                                              
cmd options                                                                   
                                                                              
positional arguments:                                                         
  path                  source code root dir                                  
                                                                              
optional arguments:                                                           
  -h, --help            show this help message and exit                       
  --config CONFIG, -c CONFIG                                                  
                        project configuration file                            
  --sonar_profile SONAR_PROFILE, -p SONAR_PROFILE                             
                        sonar quality profile                                 
  --jobs JOBS, -j JOBS  max sonar scanner job count                           
  --dry_run, -dr        dry run                                               
  --filter FILTER [FILTER ...], -f FILTER [FILTER ...]                        
                        filter list                                           
  --skip_failure, -sf   skip failure                                          
  --multi_include_samesrcdir, -m                                              
                        multi_include_samesrcdir                                                                   
```

# 配置文件
```xml
<conf>
	<system version="trunk" name="vc-example" relative-path="build">
		<subsystem name="A" relative-path="A">
            <project name="A" file="A.sln" />
    </subsystem>
		<subsystem name="B" relative-path="B">
            <project name="B" file="B.sln" excludes="B" />
    </subsystem>        
	</system>   
</conf> 
```
* system.version: 用于sonar工程的版本信息；
* relative-path: 代码工程文件相对命令行path参数的路径；
* project.file: 代码工程文件名，相对relative-path路径，vc为*.sln文件，nb为project.properites文件，mvn为pom.xml文件；
* name: 生成sonar工程的key，形如system.name:subsystem.name_project.name:projectname，其中projectname从project.file文件提取；project.name可以没有，则key为system.name:subsystem.name:projectname。
* project.excludes: 排除的工程名，逗号分隔

# example
* vc：针对VC工程，执行vc.bat
* nb：针对Netbeans RCP工程，执行nb.bat
* mvn：针对mvn工程，执行mvn.bat
