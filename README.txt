一、操作步骤
1、下载源码并进行编译
$ git clone https://github.com/ZVampirEM77/ceph.git
$ cd ceph
$ git fetch
$ git checkout wip-suyan-subuser-usage-log
$ git branch
$ ./install-deps.sh # 首次编译的话需要先安装依赖
$ ./autogen.sh
$ ./configure
$ make -j4

#至此支持子账户统计功能的Ceph分支源码编译完成
#下面开始运行测试该功能

2、运行测试(手动启动ceph集群)
$ cd $CEPH_PATH/src    # 进入 vstart.sh所在目录，后续所有的可执行程序都在这个目录里
$ CEPH_NUM_MON=1 CEPH_NUM_OSD=3 CEPH_NUM_MDS=0 ./vstart.sh  -n -X -l -r -k    # 启动测试集群
# 检查是否开启记录 subuser usage log 功能
# 此处需要说明的是，可以采用两种方式来修改rgw_enable_usage_log和rgw_enable_usage_log_at_subuser_level两项的配置：
# 1、在src/common/目录下的config_opts.h文件中，是这两项的配置定义，可以通过修改config_opts.h中的配置来对其进行选项开关；
#    但需要注意的是，通过这种方式修改配置，需要重新编译ceph使配置生效
# 2、也可以直接修改src目录下的ceph.conf，该文件是根据src/common/config_opts.h在ceph集群启动时生成的，但需要注意的是，默认
#    情况下，vstart.sh在每次执行时都会根据config_opts.h重新生成ceph.conf文件，但若要通过修改ceph.conf来修改集群配置，相当于
#    要让vstart.sh在启动集群时，读取本地已有的ceph.conf文件，所以需要在启动参数中加入-k
#    -k keep old configuration files
$ ./ceph daemon osd.0 config show  | grep rgw_enable_usage_log 
*** DEVELOPER MODE: setting PATH, PYTHONPATH and LD_LIBRARY_PATH ***
    "rgw_enable_usage_log": "true",
    "rgw_enable_usage_log_at_subuser_level": "true",

# 可以直接使用测试脚本来创建测试所需的账户和子账户
$ python S3SubuserCLIApiAutoTest.py --ceph-path=$CEPH_PATH/src --opt-type=create_user      #创建s3类型的测试账户和子账户
$ python SwiftSubuserCLIApiAutoTest.py --ceph-path=$CEPH_PATH/src --opt-type=create_user      #创建swift类型的账户和子账户

# 账户创建完毕后，就可以开始功能测试，直接使用测试脚本进行测试
$ python S3SubuserCLIApiAutoTest.py --ceph-path=$CEPH_PATH/src --opt-type=run_test      #对s3类型的账户和子账户统计功能的CLI API进行测试
$ python SwiftSubuserCLIApiAutoTest.py --ceph-path=$CEPH_PATH/src --opt-type=run_test      #对swift类型的账户和子账户统计功能的CLI API进行测试
# 需要特别注意的一点是，HTTP API测试脚本中只进行测试处理，所以HTTP API的测试脚本一定要在CLI的测试脚本创建完账户和子账户后才能执行
$ python S3SubuserHTTPApiAutoTest.py        #对s3类型的账户和子账户统计功能的HTTP API进行测试
$ python SwiftSubuserHTTPApiAutoTest.py     #对swift类型的账户和子账户统计功能的HTTP API进行测试

3、运行测试(通过脚本启动ceph集群)
# 也可以直接通过测试脚本启动ceph集群
$ python S3SubuserCLIApiAutoTest.py --ceph-path=$CEPH_PATH/src --opt-type=start   # S3类型CLI测试脚本和Swift类型CLI测试脚本都支持启动ceph，执行一个即可

然后即可开始从上面介绍的创建账户和子账户的操作进行功能测试。


二、测试脚本使用说明
因为HTTP API的自动化测试脚本只进行测试处理操作，所以不需多做介绍，主要对CLI API的自动化测试脚本的使用进行介绍

当前s3和swift CLI API的测试脚本支持两个输入参数：
--ceph-path    --   指定ceph vstart.sh所在目录(仅针对J版而言)
--opt-type     --   指定所要进行的操作类型

当前s3和swift CLI API的测试脚本均支持四种操作处理：
1、start  --  启动测试集群
2、restart   --   重启测试集群
3、create_user  --  创建测试所需账户和子账户
4、run_test    --   进行测试处理

***这里需要着重指出的是，当前四个自动化测试脚本对于start_time和end_time两个参数的测试，均需要手动去对这两个参数进行指定，具体为在
class Tester中的  m_start_time_stamp和m_end_time_stamp两个变量，测试时需要 根据具体需求，手动修改。
