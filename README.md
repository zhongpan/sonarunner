# sonarunner
sonarrunner用于从各种IDE工程执行sonar检查并上传到服务端。

# 支持的IDE工程类型
* VC解决方案，vcproj和vcxproj.
* Netbeans RCP工程
* mvn工程

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
  --dry_run, -d         dry run                                                       
  --filter FILTER [FILTER ...], -f FILTER [FILTER ...]                                
                        filter list                                                   
  --skip_failure, -sf   skip failure                                                  
  --multi_include_samesrcdir, -m                                                      
                        multi_include_samesrcdir                                      
```
