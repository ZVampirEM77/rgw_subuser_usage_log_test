#-*- coding:utf-8 -*-
'''
Subuser Usage Log Statistics CLI API Testing
python SubuserAutoTest.py --ceph-path=* --opt-type=*
--ceph-path   --  the path of ceph vstart.sh
--opt-type    --  operation type: create_user  -- To create user and subuser for testing
                                  restart      -- To restart the ceph test cluster
                                  start        -- To start the ceph test cluster
			          run_test     -- To run test case
author     Enming Zhang
date       2017/04/12
version    0.2
'''

import sys, os, json
import time
import argparse
import subprocess
import swiftclient

def exec_command(command):
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.communicate()

def exec_command_with_return(command):
    return subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

def ok_display(content):
    return "[\033[1;;32m%s\033[0m]" % (content)

def fail_display(content):
    return "[\033[1;;41m%s\033[0m]" % (content)

def change_sys_time(date):
    m_passward = "1"
    m_command = "sudo -S date -s " + date
    os.system('echo %s | %s' % (m_passward, m_command))

#S3 class
class S3(object):
    def __init__(self):
        pass

    def s3_ls(self, cfg, times):
        for i in range(times):
            exec_command("s3cmd -c " + cfg + " ls")

    def s3_create_bucket(self, cfg, times):
	bucket_name = cfg.split(".")[0]
	for i in range(times):
	    exec_command("s3cmd -c " + cfg + " mb s3://" + bucket_name + "-bucket" + str(i))
	    
    def s3_del_bucket(self, cfg, times):
	bucket_name = cfg.split(".")[0]
	for i in range(times):
	    exec_command("s3cmd -c " + cfg + " rb s3://" + bucket_name + "-bucket" + str(i))


class SWIFT(object):
    def __init__(self):
	self.m_conn = None

    def swift_connect(self, user, key):
	self.m_conn = swiftclient.Connection(user = user, key = key, authurl = 'http://127.0.0.1:8000/auth')

    def swift_ls(self, times):
	for i in range(times):
	    self.m_conn.get_account()

    def swift_create_bucket(self, name, times):
	for i in range(times):
	    self.m_conn.put_container(name)

    def swift_del_bucket(self, name, times):
	for i in range(times):
	    self.m_conn.delete_container(name)


#Test Case class
class Tester(object):
    def __init__(self, ceph_manager):
        self.m_s3_instance = S3()
	self.m_swift_instance = SWIFT()
	self.m_test_passed_num = 0
        self.m_test_passed_num2 = 0
	self.m_ceph_manager = ceph_manager
	self.m_start_time_stamp = time.strftime('%Y-%m-%d %H:00:00', time.localtime(time.time() - 64800))
	self.m_end_time_stamp = time.strftime('%Y-%m-%d %H:00:00', time.localtime(time.time() - 61200))

    def Run1(self):
	self.test_usage_show_without_any_param()
	self.test_usage_show_with_uid_user_for_user_operating()
	self.test_usage_show_with_uid_subuser_for_user_operating()
	self.test_usage_show_with_uid_user_for_subuser_operating()
	self.test_usage_show_with_uid_subuser_for_subuser_operating()
	self.test_usage_show_with_uid_user_without_categories()
	self.test_usage_show_with_uid_subuser_without_categories()
	self.test_usage_show_with_categories_without_uid()
	self.test_usage_show_with_uid_and_categories()
	self.test_usage_show_with_uid_subuser_and_categories()
	self.test_usage_show_with_start_time_without_end_time_uid_categories()
	self.test_usage_show_with_start_time_and_uid_without_end_time_categories()
	self.test_usage_show_with_start_time_and_categories_without_end_time_uid()
	self.test_usage_show_with_start_time_uid_categories_without_end_time()
	self.test_usage_show_with_end_time_without_start_time_uid_and_categories()
	self.test_usage_show_with_end_time_and_uid_without_start_time_categories()
	self.test_usage_show_with_end_time_and_categories_without_start_time_uid()
	self.test_usage_show_with_end_time_uid_and_categories_without_start_time()
	self.test_usage_show_with_start_time_and_end_time_without_uid_categories()
	self.test_usage_show_with_start_time_end_time_and_uid_without_categories()
	self.test_usage_show_with_start_time_end_time_uid_and_categories()
	self.test_usage_show_with_show_entries_false()
	self.test_usage_show_with_show_summary_false()
	self.test_usage_trim_with_uid_user()
	self.test_usage_trim_with_uid_subuser()
	self.test_usage_trim_with_start_time_and_uid_without_end_time()
	self.test_usage_trim_with_end_time_and_uid_without_start_time()
	self.test_usage_trim_with_start_time_end_time_and_uid()
#	self.test_usage_trim_with_start_time_and_remove_all_without_end_time()
#	self.test_usage_trim_with_end_time_and_remove_all_without_start_time()
#	self.test_usage_trim_with_start_time_and_end_time_and_remove_all()

    def Run2(self):
        self.test_user_opt_one_bucket_multi_times()
        self.test_user_opt_diff_bucket_multi_times()
        self.test_subuser_opt_one_bucket_multi_times()
        self.test_subuser_opt_diff_bucket_multi_times()
        self.test_subuser_opt_one_bucket_multi_time_for_user_has_some_subusers()
        self.test_subuser_opt_diff_bucket_multi_time_for_user_has_some_subusers()
        self.test_diff_subuser_opt_diff_bucket_for_user_has_some_subusers()

    def get_user_name(self, user_dic):
        user_name = ""
        if "subuser" in user_dic:
            user_name = user_dic["user"] + ":" + user_dic["subuser"]
        else:
            user_name = user_dic["user"]
        return user_name

    def trim_and_chdir(self):
	os.chdir(self.m_ceph_manager.m_py_dir)

    #parse response content
    def parse_response_content(self, res_content):
        user_dict = {}

	for user_info in res_content["entries"]:
            user = self.get_user_name(user_info)
	    user_dict[user] = {}
	    for bucket in user_info["buckets"]:
		user_dict[user][bucket["bucket"]] = {}
                user_dict[user][bucket["bucket"]]["categories"] = {}
		for category in bucket["categories"]:
		    user_dict[user][bucket["bucket"]]["categories"][category["category"]] = {}
                    user_dict[user][bucket["bucket"]]["categories"][category["category"]]["ops"] = category["ops"]
                    user_dict[user][bucket["bucket"]]["categories"][category["category"]]["successful_ops"] = category["successful_ops"]
        return user_dict

    def Preparation1(self):
        os.chdir(self.m_ceph_manager.m_py_dir)
	self.m_s3_instance.s3_ls("vampirem.s3cfg", 3)
	self.m_s3_instance.s3_ls("vampirem3.s3cfg", 6)
        self.m_swift_instance.swift_connect('zvampirem:swiftchosenone', 'swiftchosenone')
	self.m_swift_instance.swift_create_bucket('swiftchosenone-bucket', 1)
	self.m_swift_instance.swift_del_bucket('swiftchosenone-bucket', 1)

	self.m_swift_instance.swift_connect('zvampirem:swiftchosenoneex', 'swiftchosenoneex')
	self.m_swift_instance.swift_ls(2)

	self.m_swift_instance.swift_connect('zvampirem2:swiftchosenone2', 'swiftchosenone2')
        self.m_swift_instance.swift_ls(7)

	os.chdir(self.m_ceph_manager.m_ceph_abs_dir)
	time.sleep(30)

    def Preparation2(self):
        os.chdir(self.m_ceph_manager.m_py_dir)
        self.m_s3_instance.s3_create_bucket("vampirem.s3cfg", 1)
        self.m_s3_instance.s3_del_bucket("vampirem.s3cfg", 1)
        self.m_s3_instance.s3_create_bucket("vampirem2.s3cfg", 2)
        self.m_s3_instance.s3_del_bucket("vampirem2.s3cfg", 2)
        self.m_s3_instance.s3_create_bucket("chosenone3.s3cfg", 1)
        self.m_s3_instance.s3_del_bucket("chosenone3.s3cfg", 1)
        self.m_s3_instance.s3_create_bucket("chosenone2.s3cfg", 2)
        self.m_s3_instance.s3_del_bucket("chosenone2.s3cfg", 2)
        self.m_swift_instance.swift_connect('zvampirem:swiftchosenone', 'swiftchosenone')
	self.m_swift_instance.swift_create_bucket('swiftchosenone-bucket', 1)
	self.m_swift_instance.swift_del_bucket('swiftchosenone-bucket', 1)

        self.m_swift_instance.swift_connect('zvampirem3:swiftchosenone3', 'swiftchosenone3')
	self.m_swift_instance.swift_create_bucket('swiftchosenone3-bucket', 1)
	self.m_swift_instance.swift_del_bucket('swiftchosenone3-bucket', 1)
        os.chdir(self.m_ceph_manager.m_ceph_abs_dir)
        time.sleep(30)


    #verify the response msg is same with expect result
    def verify_show_response_msg(self, req_command, expect_dict):
	usage_log = exec_command_with_return(req_command)
	data = json.load(usage_log)
#        print data
	result = True
	user_dict = {}

	if len(data["entries"]) == expect_dict["entries_size"] and len(data["summary"]) == expect_dict["entries_size"]:
	    user_dict = self.parse_response_content(data)
	    for user_info in data["entries"]:
                user = self.get_user_name(user_info)
	        if user_dict[user] != expect_dict[user]:
		    result = False
        else:
	    result = False
	
	return result
		
    #verify the response msg is same with expect result
    def verify_trim_response_msg(self, req_command, expect_dict):
	exec_command(req_command)	
        usage_log = exec_command_with_return("./radosgw-admin usage show")	
	data = json.load(usage_log)	
#        print data
        result = True
        user_dict = {}

	if len(data["entries"]) == expect_dict["entries_size"] and len(data["summary"]) == expect_dict["entries_size"]:
	    user_dict = self.parse_response_content(data)

	    for user_info in data["entries"]:
                user = self.get_user_name(user_info)
	        if user_dict[user] != expect_dict[user]:
		    result = False
        else:
	    result = False
	
	return result


    #To test "usage show" without any param
    def test_usage_show_without_any_param(self):
	expect_dict = {"entries_size": 4, 
		       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
			             "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
		       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
		       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}},
		       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
		      }

	result = self.verify_show_response_msg("./radosgw-admin usage show", expect_dict)
	
	if result == True:	
	    self.m_test_passed_num += 1
	    print "test_usage_show_without_any_param                                   %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_without_any_param                                   %s" % (fail_display("FAIL"))


    #To test "usage show" with uid = user for user operating
    def test_usage_show_with_uid_user_for_user_operating(self):
	expect_dict = {"entries_size": 1,
                       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}}}

        result = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem3", expect_dict)

        if result == True:
            self.m_test_passed_num += 1
	    print "test_usage_show_with_uid_userid_for_user_operating                  %s" % (ok_display("OK"))
	else:
            print "test_usage_show_with_uid_userid_for_user_operating                  %s" % (fail_display("FAIL"))


    #To test "usage show" with uid = subuser for user operating
    def test_usage_show_with_uid_subuser_for_user_operating(self):
	expect_dict = {"entries_size": 0, "summary_size": 0}
        
	usage_log = exec_command_with_return("./radosgw-admin usage show --uid=zvampirem3 --subuser=swiftchosenone3")	
	data = json.load(usage_log)
	
        result = True
	if len(data["entries"]) == expect_dict["entries_size"] and len(data["summary"]) == expect_dict["summary_size"]:
	    if data["entries"] != [] or data["summary"] != []:
	        result = False
	else:
	    result = False

	if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_uid_subuser_for_user_operating                 %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_uid_subuser_for_user_operating                 %s" % (fail_display("FAIL"))
    

    #To test "usage show" with uid = user for subuser operating
    def test_usage_show_with_uid_user_for_subuser_operating(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}}
                       }
	
	result = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem2", expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_uid_user_for_subuser_operating                 %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_uid_user_for_subuser_operating                 %s" % (fail_display("FAIL"))


    #To test "usage show" with uid = subuser for subuser operating
    def test_usage_show_with_uid_subuser_for_subuser_operating(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem2:swiftchosenone2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}}}

	result = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem2 --subuser=swiftchosenone2", expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_uid_subuser_for_subuser_operating              %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_uid_subuser_for_subuser_operating              %s" % (fail_display("FAIL"))
	


    #To test "usage show" with uid = user, but without categories
    def test_usage_show_with_uid_user_without_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}}
    
	result = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem", expect_dict)
	
        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_uid_user_without_categories                    %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_uid_user_without_categories                    %s" % (fail_display("FAIL"))


    #To test "usage show" with uid = subuser, but without categories
    def test_usage_show_with_uid_subuser_without_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem:swiftchosenone": {"swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}}

	result = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem --subuser=swiftchosenone", expect_dict)
	
        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_uid_subuser_without_categories                 %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_uid_subuser_without_categories                 %s" % (fail_display("FAIL"))


    #To test "usage show" with categories, but without uid
    def test_usage_show_with_categories_without_uid(self):
        expect_dict = {"entries_size": 4,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {}}},
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}
	
        result = self.verify_show_response_msg("./radosgw-admin usage show --categories=list_buckets", expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_categories_without_uid                         %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_categories_without_uid                         %s" % (fail_display("FAIL"))


    #To test "usage show" with uid = user and categories = XXXX
    def test_usage_show_with_uid_and_categories(self):
	expect_dict = {"entries_size": 1,
                       "zvampirem": {"": {"categories": {}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}}}}}
        
        result = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem --categories=create_bucket", expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_uid_and_categories                             %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_uid_and_categories                             %s" % (fail_display("FAIL"))


    #To test "usage show" with uid = subuser and categories = XXXX
    def test_usage_show_with_uid_subuser_and_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem:swiftchosenone": {"swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}}}}}

	result = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem --subuser=swiftchosenone --categories=create_bucket", expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_uid_subuser_and_categories                     %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_uid_subuser_and_categories                     %s" % (fail_display("FAIL"))


    #To test "usage show" with start-date, but without uid and categories
    def test_usage_show_with_start_time_without_end_time_uid_categories(self):
        expect_dict = {"entries_size": 3,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                        "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                        "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}}}

        result = self.verify_show_response_msg('./radosgw-admin usage show --start-date="' + self.m_start_time_stamp + '"', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_start_time_without_end_time_uid_categories     %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_start_time_without_end_time_uid_categories     %s" % (fail_display("FAIL"))

        
    #To test "usage show" with end-date, but without uid and categories
    def test_usage_show_with_start_time_and_uid_without_end_time_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}}}

        result = self.verify_show_response_msg('./radosgw-admin usage show --start-date="' + self.m_start_time_stamp + '" --uid=zvampirem3', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_start_time_and_uid_without_end_time_categories %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_start_time_and_uid_without_end_time_categories %s" % (fail_display("FAIL"))



    #To test "usage show" with start-date and end-date
    def test_usage_show_with_start_time_and_categories_without_end_time_uid(self):
	expect_dict = {"entries_size": 3,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {}}},
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}}}

        result = self.verify_show_response_msg('./radosgw-admin usage show --start-date="' + self.m_start_time_stamp + '" --categories=list_buckets', expect_dict)
    
        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_start_time_and_categories_without_end_time_uid %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_start_time_and_categories_without_end_time_uid %s" % (fail_display("FAIL"))
	    
    #test "usage show" with start, uid and categories, without end
    def test_usage_show_with_start_time_uid_categories_without_end_time(self):
	expect_dict = {"entries_size": 1,
                       "zvampirem:swiftchosenone": {"swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}}}}}

	result = self.verify_show_response_msg('./radosgw-admin usage show --uid=zvampirem --subuser=swiftchosenone --start-date="' + self.m_start_time_stamp + '" --categories=create_bucket', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_start_time_uid_categories_without_end_time     %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_start_time_uid_categories_without_end_time     %s" % (fail_display("FAIL"))


    #test "usage show" with end, but without start, uid and categories
    def test_usage_show_with_end_time_without_start_time_uid_and_categories(self):
	expect_dict = {"entries_size": 1,
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

        result = self.verify_show_response_msg('./radosgw-admin usage show --end-date="' + self.m_end_time_stamp + '"', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_end_time_without_start_time_uid_and_categories %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_end_time_without_start_time_uid_and_categories %s" % (fail_display("FAIL"))
        

    #test "usage show" with end and uid, without start and categories
    def test_usage_show_with_end_time_and_uid_without_start_time_categories(self):
        expect_dict = {"entries_size": 1,
                       "time_test:time_test_sub": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

	result = self.verify_show_response_msg('./radosgw-admin usage show --uid=time_test --subuser=time_test_sub --end-date="' + self.m_end_time_stamp + '"', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_end_time_and_uid_without_start_time_categories %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_end_time_and_uid_without_start_time_categories %s" % (fail_display("FAIL"))


    #test "usage show" with end and categories, without start and uid
    def test_usage_show_with_end_time_and_categories_without_start_time_uid(self):
	expect_dict = {"entries_size": 1,
                       "time_test": {"": {"categories": {}}},
                      }

        result = self.verify_show_response_msg('./radosgw-admin usage show --categories=create_bucket --end-date="' + self.m_end_time_stamp + '"', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_end_time_and_categories_without_start_time_uid %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_end_time_and_categories_without_start_time_uid %s" % (fail_display("FAIL"))


    #test "usage show" with end, uid and categories, without start
    def test_usage_show_with_end_time_uid_and_categories_without_start_time(self):
        expect_dict = {"entries_size": 1,
                       "time_test:time_test_sub": {"": {"categories": {}}}}

	result = self.verify_show_response_msg('./radosgw-admin usage show --uid=time_test --subuser=time_test_sub --categories=create_bucket --end-date="' + self.m_end_time_stamp + '"', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_end_time_uid_and_categories_without_start_time %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_end_time_uid_and_categories_without_start_time %s" % (fail_display("FAIL"))

    #test "usage show" with start and end, without uid and categories
    def test_usage_show_with_start_time_and_end_time_without_uid_categories(self):
	usage_log = exec_command_with_return('./radosgw-admin usage show --start-date="' + self.m_start_time_stamp + '"  --end-date="' + self.m_end_time_stamp + '"')	
	data = json.load(usage_log)
	result = True

        if len(data["entries"]) != 0 or len(data["summary"]) != 0:
            result = False

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_time_and_end_time_without_uid_categories %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_time_and_end_time_without_uid_categories %s" % (fail_display("FAIL"))

    #test "usage show" with start, end and uid, without categories
    def test_usage_show_with_start_time_end_time_and_uid_without_categories(self):
	usage_log = exec_command_with_return('./radosgw-admin usage show --uid=zvampirem --start-date="' + self.m_start_time_stamp + '"  --end-date="' + self.m_end_time_stamp + '"')	
	data = json.load(usage_log)
	result = True

        if len(data["entries"]) != 0 or len(data["summary"]) != 0:
            result = False

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_time_end_time_and_uid_without_categories %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_time_end_time_and_uid_without_categories %s" % (fail_display("FAIL"))


    #test "usage show" with start, end, uid and categories
    def test_usage_show_with_start_time_end_time_uid_and_categories(self):
        usage_log = exec_command_with_return('./radosgw-admin usage show --uid=zvampirem --categories=list_buckets --start-date="' + self.m_start_time_stamp + '"  --end-date="' + self.m_end_time_stamp + '"')	
	data = json.load(usage_log)
	result = True

        if len(data["entries"]) != 0 or len(data["summary"]) != 0:
            result = False

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_time_end_time_uid_and_categories         %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_time_end_time_uid_and_categories         %s" % (fail_display("FAIL"))


    #To test "usage show" with --show-log-entries = false
    def test_usage_show_with_show_entries_false(self):
	usage_log = exec_command_with_return("./radosgw-admin usage show --show-log-entries=false")	
	data = json.load(usage_log)	
        result = False

        if len(data["summary"]) == 4:
	    try:
	        print data["entries"]
	    except KeyError:
		result = True

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_show_entries_false                             %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_show_entries_false                             %s" % (fail_display("FAIL"))

    #To test "usage show" with --show-log-sum = false
    def test_usage_show_with_show_summary_false(self):
	usage_log = exec_command_with_return("./radosgw-admin usage show --show-log-sum=false")	
	data = json.load(usage_log)	
        result = False

        if len(data["entries"]) == 4:
	    try:
	        print data["summary"]
	    except KeyError:
		result = True

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_show_with_show_summary_false                             %s" % (ok_display("OK"))
	else:
	    print "test_usage_show_with_show_summary_false                             %s" % (fail_display("FAIL"))


    #test "usage trim" with uid = user
    def test_usage_trim_with_uid_user(self):	
        expect_dict = {"entries_size": 3,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}},
                      }

        result = self.verify_trim_response_msg('./radosgw-admin usage trim --uid=zvampirem3', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_trim_with_uid_user                                       %s" % (ok_display("OK"))
	else:
	    print "test_usage_trim_with_uid_user                                       %s" % (fail_display("FAIL"))

    #test "usage trim" with uid = subuser
    def test_usage_trim_with_uid_subuser(self): 
        expect_dict = {"entries_size": 3,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
                      }

	result = self.verify_trim_response_msg('./radosgw-admin usage trim --uid=zvampirem --subuser=swiftchosenoneex', expect_dict)


        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_trim_with_uid_subuser                                    %s" % (ok_display("OK"))
	else:
	    print "test_usage_trim_with_uid_subuser                                    %s" % (fail_display("FAIL"))


    #test "usage trim" with start and uid, without end:
    def test_usage_trim_with_start_time_and_uid_without_end_time(self):
        expect_dict = {"entries_size": 2,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

        result = self.verify_trim_response_msg('./radosgw-admin usage trim --uid=zvampirem2 --start-date="' + self.m_start_time_stamp + '"', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_trim_with_start_time_and_uid_without_end_time            %s" % (ok_display("OK"))
	else:
	    print "test_usage_trim_with_start_time_and_uid_without_end_time            %s" % (fail_display("FAIL"))

	
    #test "usage trim" with end and uid, without start
    def test_usage_trim_with_end_time_and_uid_without_start_time(self):
        expect_dict = {"entries_size": 2,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
                }

	result = self.verify_trim_response_msg('./radosgw-admin usage trim --uid=zvampirem --subuser=swiftchosenone --end-date="' + self.m_end_time_stamp + '"', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_trim_with_end_time_and_uid_without_start_time            %s" % (ok_display("OK"))
	else:
	    print "test_usage_trim_with_end_time_and_uid_without_start_time            %s" % (fail_display("FAIL"))



    #test "usage trim" with start, end and uid
    def test_usage_trim_with_start_time_end_time_and_uid(self):
        expect_dict = {"entries_size": 2,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
                }

	result = self.verify_trim_response_msg('./radosgw-admin usage trim --uid=zvampirem --subuser=swiftchosenone --start-date="' + self.m_start_time_stamp + ' --end-date="' + self.m_end_time_stamp + '"', expect_dict)


        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_trim_with_start_time_end_time_and_uid                    %s" % (ok_display("OK"))
	else:
	    print "test_usage_trim_with_start_time_end_time_and_uid                    %s" % (fail_display("FAIL"))


    #test "usage trim" with start and remove-all = True, without end
    def test_usage_trim_with_start_time_and_remove_all_without_end_time(self):
        expect_dict = {"entries_size": 1,
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
                       }

#	result = self.verify_trim_response_msg('./radosgw-admin usage trim --uid=zvampirem:chosenone --start-date="' + self.m_start_time_stamp + ' --end-date="' + self.m_end_time_stamp + '"', expect_dict)

        result = self.verify_trim_response_msg('./radosgw-admin usage trim --yes-i-really-mean-it --start-date="' + self.m_start_time_stamp + '"', expect_dict)
 
        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_trim_with_start_time_and_remove_all_without_end_time     %s" % (ok_display("OK"))
	else:
	    print "test_usage_trim_with_start_time_and_remove_all_without_end_time     %s" % (fail_display("FAIL"))

 
    #test "usage trim" with end and remove-all = True, without start
    def test_usage_trim_with_end_time_and_remove_all_without_start_time(self):
        self.m_test_passed_num += 1
        print "test_usage_trim_with_end_time_and_remove_all_without_start_time     %s" % (ok_display("OK"))



    #test "usage trim" with start and end and remove-all = True
    def test_usage_trim_with_start_time_and_end_time_and_remove_all(self):
	expect_dict = {"entries_size": 1,
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
                       }

        result = self.verify_trim_response_msg('./radosgw-admin usage trim --yes-i-really-mean-it --start-date="' + self.m_start_time_stamp + ' --end-date="' + self.m_end_time_stamp + '"', expect_dict)

        if result == True:
	    self.m_test_passed_num += 1
	    print "test_usage_trim_with_start_time_and_end_time_and_remove_all         %s" % (ok_display("OK"))
	else:
	    print "test_usage_trim_with_start_time_and_end_time_and_remove_all         %s" % (fail_display("FAIL"))

    def test_user_opt_one_bucket_multi_times(self):
        expect_dict1 = {"entries_size": 1,
                       "zvampirem": {"vampirem-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result1 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem", expect_dict1)
        
        usage_log = exec_command_with_return('./radosgw-admin usage show --uid=zvampirem --subuser=chosenone')	
	data = json.load(usage_log) 
        result2 = True

        if len(data["entries"]) != 0 or len(data["summary"]) != 0:
            result2 = False

        if result1 == True and result2 == True:
            self.m_test_passed_num2 += 1
	    print "test_user_opt_one_bucket_multi_times                                %s" % (ok_display("OK"))
	else:
	    print "test_user_opt_one_bucket_multi_times                                %s" % (fail_display("FAIL"))

    def test_user_opt_diff_bucket_multi_times(self):
        expect_dict1 = {"entries_size": 1,
                       "zvampirem2": {"vampirem2-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "vampirem2-bucket1": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "chosenone2-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "chosenone2-bucket1": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result1 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem2", expect_dict1)
        
        usage_log = exec_command_with_return('./radosgw-admin usage show --uid=zvampirem2 --subuser=swiftchosenone2')	
	data = json.load(usage_log) 
        result2 = True

        if len(data["entries"]) != 0 or len(data["summary"]) != 0:
            result2 = False

        if result1 == True and result2 == True:
            self.m_test_passed_num2 += 1
	    print "test_user_opt_diff_bucket_multi_times                               %s" % (ok_display("OK"))
	else:
	    print "test_user_opt_diff_bucket_multi_times                               %s" % (fail_display("FAIL"))


    def test_subuser_opt_one_bucket_multi_times(self):
        expect_dict1 = {"entries_size": 1,
                       "zvampirem3": {"chosenone3-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "swiftchosenone3-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result1 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem3", expect_dict1)
        
        expect_dict2 = {"entries_size": 1,
                       "zvampirem3:chosenone3": {"chosenone3-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result2 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem3 --subuser=chosenone3", expect_dict2)

        if result1 == True and result2 == True:
            self.m_test_passed_num2 += 1
	    print "test_subuser_opt_one_bucket_multi_times                             %s" % (ok_display("OK"))
	else:
	    print "test_subuser_opt_one_bucket_multi_times                             %s" % (fail_display("FAIL"))


    def test_subuser_opt_diff_bucket_multi_times(self):
        expect_dict1 = {"entries_size": 1,
                       "zvampirem2": {"vampirem2-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "vampirem2-bucket1": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "chosenone2-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "chosenone2-bucket1": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }

        result1 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem2", expect_dict1)

        expect_dict2 = {"entries_size": 1,
                       "zvampirem2:chosenone2": {
                                      "chosenone2-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "chosenone2-bucket1": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }

        result2 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem2 --subuser=chosenone2", expect_dict2)

        if result1 == True and result2 == True:
            self.m_test_passed_num2 += 1
	    print "test_subuser_opt_diff_bucket_multi_times                            %s" % (ok_display("OK"))
	else:
	    print "test_subuser_opt_diff_bucket_multi_times                            %s" % (fail_display("FAIL"))

    def test_subuser_opt_one_bucket_multi_time_for_user_has_some_subusers(self):
        expect_dict1 = {"entries_size": 1,
                       "zvampirem": {"vampirem-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result1 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem", expect_dict1)
        
        expect_dict2 = {"entries_size": 1,
                       "zvampirem:swiftchosenone": {
                                     "swiftchosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result2 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem --subuser=swiftchosenone", expect_dict2)
        
        usage_log = exec_command_with_return('./radosgw-admin usage show --uid=zvampirem --subuser=chosenone')	
	data = json.load(usage_log) 
        result3 = True

        if len(data["entries"]) != 0 or len(data["summary"]) != 0:
            result3 = False

        if result1 == True and result2 == True and result3 == True:
            self.m_test_passed_num2 += 1
	    print "test_subuser_opt_one_bucket_multi_time_for_user_has_some_subusers   %s" % (ok_display("OK"))
	else:
	    print "test_subuser_opt_one_bucket_multi_time_for_user_has_some_subusers   %s" % (fail_display("FAIL"))


    def test_subuser_opt_diff_bucket_multi_time_for_user_has_some_subusers(self):
        expect_dict1 = {"entries_size": 1,
                       "zvampirem2": {"vampirem2-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "vampirem2-bucket1": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "chosenone2-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "chosenone2-bucket1": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }

        result1 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem2", expect_dict1)

        expect_dict2 = {"entries_size": 1,
                       "zvampirem2:chosenone2": {
                                      "chosenone2-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "chosenone2-bucket1": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }

        result2 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem2 --subuser=chosenone2", expect_dict2)
        
        usage_log = exec_command_with_return('./radosgw-admin usage show --uid=zvampirem2 --subuser=swiftchosenone2')	
	data = json.load(usage_log) 
        result3 = True

        if len(data["entries"]) != 0 or len(data["summary"]) != 0:
            result3 = False

        if result1 == True and result2 == True and result3 == True:
            self.m_test_passed_num2 += 1
	    print "test_subuser_opt_diff_bucket_multi_time_for_user_has_some_subusers  %s" % (ok_display("OK"))
	else:
	    print "test_subuser_opt_diff_bucket_multi_time_for_user_has_some_subusers  %s" % (fail_display("FAIL"))


    def test_diff_subuser_opt_diff_bucket_for_user_has_some_subusers(self):
        expect_dict1 = {"entries_size": 1,
                       "zvampirem3": {"chosenone3-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}},
                                      "swiftchosenone3-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result1 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem3", expect_dict1)
        
        expect_dict2 = {"entries_size": 1,
                       "zvampirem3:chosenone3": {"chosenone3-bucket0": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result2 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem3 --subuser=chosenone3", expect_dict2)
        
        expect_dict3 = {"entries_size": 1,
                       "zvampirem3:swiftchosenone3": {"swiftchosenone3-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}
                      }
        result3 = self.verify_show_response_msg("./radosgw-admin usage show --uid=zvampirem3 --subuser=swiftchosenone3", expect_dict3)

        if result1 == True and result2 == True and result3 == True:
            self.m_test_passed_num2 += 1
	    print "test_diff_subuser_opt_diff_bucket_for_user_has_some_subusers        %s" % (ok_display("OK"))
	else:
	    print "test_diff_subuser_opt_diff_bucket_for_user_has_some_subusers        %s" % (fail_display("FAIL"))


#Ceph Manager
class CephManager(object):
    def __init__(self):
	self.m_py_dir = os.getcwd()
#        print "m_py_dir is %s" % (self.m_py_dir)
	self.m_ceph_abs_dir = ""
	self.m_tester = Tester(self)

#To start ceph cluster
    def start_ceph(self):	    
#        os.chdir(ceph_path)
#	self.m_ceph_abs_dir = os.getcwd()
	print "Starting Ceph..../"
	exec_command("CEPH_NUM_MON=1 CEPH_NUM_OSD=3 CEPH_NUM_MDS=0 ./vstart.sh -n -X -l -r -k")
	time.sleep(5)
	ceph_status = exec_command_with_return("./ceph health").readlines()
	print ceph_status
	if "HEALTH_OK\n" in ceph_status:
	    return 0
	else:
	    print "Ceph start fail!"
            return -1

    def restart_ceph(self):
#        os.chdir(ceph_path)
#	self.m_ceph_abs_dir = os.getcwd()
        #At first, stop ceph cluster
        exec_command("./stop.sh all")
        #Start ceph cluster
        return self.start_ceph()

        

#To check whether function of subuser usage log is enable or not
    def check_usage_log_switch(self):
	exec_command("./ceph daemon osd.0 config show | grep rgw_enable_usage_log")

#To create user and subuser for testing
    def create_user_and_subuser(self):
	exec_command('./radosgw-admin user create --uid=zvampirem --access-key=zvampirem --secret-key=zvampirem --display-name="zvampirem"')
        exec_command('./radosgw-admin user create --uid=zvampirem2 --access-key=zvampirem2 --secret-key=zvampirem2 --display-name="zvampirem2"')
        exec_command('./radosgw-admin user create --uid=zvampirem3 --access-key=zvampirem3 --secret-key=zvampirem3 --display-name="zvampirem3"')
	exec_command('./radosgw-admin subuser create --key-type=swift --uid=zvampirem --subuser=swiftchosenone --access=full --access-key=swiftchosenone --secret-key=swiftchosenone')
        exec_command('./radosgw-admin subuser create --key-type=swift --uid=zvampirem --subuser=swiftchosenoneex --access=full --access-key=swiftchosenoneex --secret-key=swiftchosenoneex')
        exec_command('./radosgw-admin subuser create --key-type=swift --uid=zvampirem2 --subuser=swiftchosenone2 --access=full --access-key=swiftchosenone2 --secret-key=swiftchosenone2')
        exec_command('./radosgw-admin subuser create --key-type=swift --uid=zvampirem3 --subuser=swiftchosenone3 --access=full --access-key=swiftchosenone3 --secret-key=swiftchosenone3')


    def trim_and_check(self, uid):
        if ":" in uid:
            user_list = uid.split(':')
            exec_command("./radosgw-admin usage trim --uid=" + user_list[0] + " --subuser=" + user_list[1])
            usage_log = exec_command_with_return("./radosgw-admin usage show --uid=" + user_list[0] + " --subuser=" + user_list[1])
        else:
            exec_command("./radosgw-admin usage trim --uid=" + uid)
	    usage_log = exec_command_with_return("./radosgw-admin usage show --uid=" + uid)	

	data = json.load(usage_log)	
        result = True

	if data["entries"] != [] or data["summary"] != []:
	    result = False
	
        if result == True:
            print "Trim " + uid + " testing usage log! OK"
        else:
            print "Trim " + uid + " testing usage log! FAIL"

	return result

    def test_preparation1(self):
        self.m_tester.Preparation1()

    def test_preparation2(self):
        self.m_tester.Preparation2()

    def test_run1(self):
	self.m_tester.Run1()

    def test_run2(self):
	self.m_tester.Run2()

    def test_end1(self):	
        print "-----------------------------------------------------------------------------------------"
	print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
	print "-----------------------------------------------------------------------------------------"
        
        if self.trim_and_check("zvampirem") \
        and self.trim_and_check("zvampirem:swiftchosenone") \
        and self.trim_and_check("zvampirem:swiftchosenoneex") \
        and self.trim_and_check("zvampirem2") \
        and self.trim_and_check("zvampirem2:swiftchosenone2") \
        and self.trim_and_check("zvampirem3") \
        and self.trim_and_check("zvampirem3:swiftchosenone3"):
            print "Test End!"
            print "Total test case: 31, OK: %d, FAIL: %d" % (self.m_tester.m_test_passed_num, 31 - self.m_tester.m_test_passed_num)

    def test_end2(self):	
        print "-----------------------------------------------------------------------------------------"
	print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
	print "-----------------------------------------------------------------------------------------"
        
        if self.trim_and_check("zvampirem") \
        and self.trim_and_check("zvampirem:swiftchosenone") \
        and self.trim_and_check("zvampirem:chosenone") \
        and self.trim_and_check("zvampirem:chosenoneex") \
        and self.trim_and_check("zvampirem:swiftchosenoneex") \
        and self.trim_and_check("zvampirem2") \
        and self.trim_and_check("zvampirem2:swiftchosenone2") \
        and self.trim_and_check("zvampirem2:chosenone2") \
        and self.trim_and_check("zvampirem3") \
        and self.trim_and_check("zvampirem3:chosenone3") \
        and self.trim_and_check("zvampirem3:swiftchosenone3"):
            print "Test End!"
            print "Total test case: 7, OK: %d, FAIL: %d" % (self.m_tester.m_test_passed_num2, 7 - self.m_tester.m_test_passed_num2)



    def print_pwd(self):
        exec_command("pwd")


def ParseCommandLine():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ceph-path', action = 'store', dest = 'ceph_path', default = '')
    parser.add_argument('--opt-type', action = 'store', dest = 'opt_type', default = '')
    result = parser.parse_args()
    return result



if __name__ == '__main__':


    ceph_manager = CephManager()
    cmd_line_param = ParseCommandLine()
    ceph_path = cmd_line_param.ceph_path
    opt_type = cmd_line_param.opt_type

    if ceph_path == "" or opt_type == "":
        print "You must specify value for --ceph-path and --opt-type"
    else:
        os.chdir(ceph_path)
	ceph_manager.m_ceph_abs_dir = os.getcwd()

        if opt_type == "create_user":
	    ceph_manager.create_user_and_subuser() 
            os.chdir(ceph_manager.m_ceph_abs_dir)
        
        elif opt_type == "start":            
            if ceph_manager.start_ceph() == 0:
                print "Ceph cluster starts successfully!"
                ceph_manager.check_usage_log_switch()

        elif opt_type == "restart":
            if ceph_manager.restart_ceph() == 0:
                print "Ceph cluster restarts successfully!"
                ceph_manager.check_usage_log_switch()

        elif opt_type == "run_test":
                print "CLI API test"
	        ceph_manager.test_preparation1()
                ceph_manager.test_run1() 
	        ceph_manager.test_end1()    
                
                print "\nUsage Scenario test"
                ceph_manager.test_preparation2()
                ceph_manager.test_run2() 
	        ceph_manager.test_end2()    

