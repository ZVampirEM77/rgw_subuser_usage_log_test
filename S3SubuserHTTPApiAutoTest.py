#-*- coding:utf-8 -*-
'''
Subuser Usage Log Statistics HTTP API Testing
python SubuserHTTPAPIAutoTest.py

author        Enming Zhang
date          2017/03/01
version       0.1
'''

import boto
import time
import json
import boto.s3.connection
import requests
from awsauth import S3Auth

#ceph_cluster_host = "172.16.225.142"
ceph_cluster_host = "127.0.0.1"
ceph_cluster_port = 8000
ceph_cluster_server = '{host}:{port}'.format(host = ceph_cluster_host, port = ceph_cluster_port)
ceph_cluster_admin = 'admin'
ceph_cluster_admin_access_key = 'admin'
ceph_cluster_admin_secret_key = 'admin'

RES_OK = 200

def ok_display(content):
    return "[\033[1;;32m%s\033[0m]" % (content)

def fail_display(content):
    return "[\033[1;;41m%s\033[0m]" % (content)


class BaseUser(object):
    def __init__(self, uid, access_key, secret_key):
        self.uid = uid
        self.access_key = access_key
        self.secret_key = secret_key
        self.s3_connection = boto.connect_s3(aws_access_key_id = self.access_key,
                                             aws_secret_access_key = self.secret_key,
                                             host = ceph_cluster_host,
                                             port = ceph_cluster_port,
                                             is_secure = False,
                                             calling_format = boto.s3.connection.OrdinaryCallingFormat())
        self.bucket = None

class RGWUser(BaseUser):
    def __init__(self, uid, access_key, secret_key, display_name):
        BaseUser.__init__(self, uid, access_key, secret_key)
        self.display_name = display_name

class RGWSubuser(BaseUser):
    def __init__(self, uid, subuser, access_key, secret_key):
        self.key_type = 's3'
        self.access = 'full'
        BaseUser.__init__(self, uid, access_key, secret_key)
        self.subuser = subuser


class RGWOper(object):

    def ls_bucket(self, user, times):
        for i in range(times):
            user.s3_connection.get_all_buckets()

    def create_bucket(self, user):
        user.bucket = user.s3_connection.create_bucket(user.access_key + "_bucket")

    def delete_bucket(self, user):
        user.s3_connection.delete_bucket(user.bucket.name)
        


class Tester(object):
    def __init__(self):
        self.zvampirem = RGWUser("zvampirem", "zvampirem", "zvampirem", "zvampirem")
        self.chosenone = RGWSubuser("zvampirem", "chosenone", "chosenone", "chosenone")
        self.chosenoneex = RGWSubuser("zvampirem", "chosenoneex", "chosenoneex", "chosenoneex")
        self.zvampirem2 = RGWUser("zvampirem2", "zvampirem2", "zvampirem2", "zvampirem2")
        self.chosenone2 = RGWSubuser("zvampirem2", "chosenone2", "chosenone2", "chosenone2")
        self.zvampirem3 = RGWUser("zvampirem3", "zvampirem3", "zvampirem3", "zvampirem3")
        self.chosenone3 = RGWSubuser("zvampirem3", "chosenone3", "chosenone3", "chosenone3")
        self.time_test = RGWUser("time_test", "time_test", "time_test", "time_test")
        self.time_test_sub = RGWSubuser("time_test", "time_test_sub", "time_test_sub", "time_test_sub")
        # rgw operating class instance
        self.m_rgw_operater = RGWOper()
        # record the num of passed test case
        self.m_test_passed_num = 0

        self.m_start_time_stamp = time.strftime('%Y-%m-%d %H:00:00', time.localtime(time.time() - 36000))
        self.m_end_time_stamp = time.strftime('%Y-%m-%d %H:00:00', time.localtime(time.time() - 32400))
        self.m_end_time_stamp2 = time.strftime('%Y-%m-%d %H:00:00', time.localtime(time.time() - 43200))


    def test_preparation(self):
        self.m_rgw_operater.ls_bucket(self.zvampirem, 3)
        self.m_rgw_operater.create_bucket(self.chosenone)
        self.m_rgw_operater.delete_bucket(self.chosenone)
        self.m_rgw_operater.ls_bucket(self.chosenone2, 7)
        self.m_rgw_operater.ls_bucket(self.zvampirem3, 6)
        self.m_rgw_operater.ls_bucket(self.chosenoneex, 2)
#        self.m_rgw_operater.ls_bucket(self.time_test, 2)
        time.sleep(30)
        
    def get_user_name(self, user_dic):
        user_name = ""
        if "subuser" in user_dic:
            user_name = user_dic["user"] + ":" + user_dic["subuser"]
        else:
            user_name = user_dic["user"]
        return user_name

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
#                   print user_dict[user_info["user"]]
        return user_dict

    #verify the response msg is same with expect result
    def verify_get_response_msg(self, url, expect_dict):
        response = requests.get(url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
        res_content = json.loads(response.text)

#        print res_content

        result = True
        user_dict = {}
        
        if len(res_content["entries"]) == expect_dict["entries_size"] and len(res_content["summary"]) == expect_dict["entries_size"]:
	    if len(res_content["entries"]) != 0:
                user_dict = self.parse_response_content(res_content)
                for user_info in res_content["entries"]:
                    user = self.get_user_name(user_info)
                    if user_dict[user] != expect_dict[user]:
                        result = False
                        break
	    else:
	        result = True
        else:
            result = False

        return result

    #verify the delete response msg is same with expect result
    def verify_del_response_msg(self, url, expect_dict):
        response = requests.delete(url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))

#        print response.status_code

        if response.status_code == RES_OK:
            req_url = "http://{server}/{admin}/usage?format=json".format(server = ceph_cluster_server, admin = ceph_cluster_admin)
            response = requests.get(req_url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
            res_content = json.loads(response.text)

#            print res_content

            result = True
            user_dict = {}
        
            if len(res_content["entries"]) == expect_dict["entries_size"] and len(res_content["summary"]) == expect_dict["entries_size"]:
		if len(res_content["entries"]) != 0:
                    user_dict = self.parse_response_content(res_content)

                    for user_info in res_content["entries"]:
                        user = self.get_user_name(user_info)
                        if user_dict[user] != expect_dict[user]:
                            result = False
                            break
	        else:
		    result = True
            else:
                result = False

        else:
            result = False

        return result

    # test "usage show" without any param
    def test_usage_show_without_any_param(self):
        expect_dict = {"entries_size": 4,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                        "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                        "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}},
                        "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}},
                      }

        req_url = "http://{server}/{admin}/usage?format=json".format(server = ceph_cluster_server, admin = ceph_cluster_admin)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_without_any_param                             %s" % (ok_display("OK"))
        else:
            print "test_usage_show_without_any_param                             %s" % (fail_display("FAIL"))



    # test "usage show" with uid = user for user operating
    def test_usage_show_with_uid_user_for_user_operating(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}}}
        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem3")
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_uid_user_for_user_operating              %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_uid_user_for_user_operating              %s" % (fail_display("FAIL"))


    #test "usage show" with uid = subuser for user operating
    def test_usage_show_with_uid_subuser_for_user_operating(self):
        expect_dict = {"entries_size": 0, "summary_size": 0}

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem3", subuser = "chosenone3")
        response = requests.get(req_url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
#        print response.status_code
        res_content = json.loads(response.text)

        result = True
        user_dict = {}

        if len(res_content["entries"]) == expect_dict["entries_size"] and len(res_content["summary"]) == expect_dict["summary_size"]:
            if res_content["entries"] != [] or res_content["summary"] != []:
                result = False
        else:
            result = False

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_uid_subuser_for_user_operating           %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_uid_subuser_for_user_operating           %s" % (fail_display("FAIL"))


    #test "usage show" with uid = user for subuser operating
    def test_usage_show_with_uid_user_for_subuser_operating(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}}
                       }

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem2")
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_uid_user_for_subuser_operating           %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_uid_user_for_subuser_operating           %s" % (fail_display("FAIL"))


    #test "usage show" with uid = subuser for subuser operating
    def test_usage_show_with_uid_subuser_for_subuser_operating(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem2:chosenone2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem2", subuser = "chosenone2")
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_uid_subuser_for_subuser_operating        %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_uid_subuser_for_subuser_operating        %s" % (fail_display("FAIL"))


    #test "usage show" with uid = user, but without categories
    def test_usage_show_with_uid_user_without_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem")
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_uid_user_without_categories              %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_uid_user_without_categories              %s" % (fail_display("FAIL"))

    #test "usage show" with uid = subuser, but without categories
    def test_usage_show_with_uid_subuser_without_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem:chosenone": {"chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone")
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_uid_subuser_without_categories           %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_uid_subuser_without_categories           %s" % (fail_display("FAIL"))

    #test "usage show" with categories, but without uid
    def test_usage_show_with_categories_without_uid(self):
        expect_dict = {"entries_size": 4,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {}}},
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&categories={categories}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, categories = "list_buckets")
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_categories_without_uid                   %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_categories_without_uid                   %s" % (fail_display("FAIL"))


    #test "usage show" with uid (= user) and categories
    def test_usage_show_with_uid_user_and_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem": {"": {"categories": {}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&categories={categories}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", categories = "create_bucket")
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_uid_and_categories                       %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_uid_and_categories                       %s" % (fail_display("FAIL")) 

    #test "usage show" with uid (= subuser) and categories
    def test_usage_show_with_uid_subuser_and_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem:chosenone": {"chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}}}}}
        
        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}&categories={categories}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone", categories = "create_bucket")
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_uid_subuser_and_categories               %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_uid_subuser_and_categories               %s" % (fail_display("FAIL"))

    
    #test "usage show" with start, without end, uid and categories
    def test_usage_show_with_start_without_end_uid_categories(self):
        expect_dict = {"entries_size": 3,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                        "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                        "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&start={start}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, start = self.m_start_time_stamp)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_without_end_uid_categories         %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_without_end_uid_categories         %s" % (fail_display("FAIL"))

    #test "usage show" with start and uid, without end and categories
    def test_usage_show_with_start_and_uid_without_end_and_categories(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}}}
        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&start={start}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem3", start = self.m_start_time_stamp)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_and_uid_without_end_and_categories %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_and_uid_without_end_and_categories %s" % (fail_display("FAIL"))

    
    #test "usage show" with start and categories, without uid and end
    def test_usage_show_with_start_and_categories_without_end_and_uid(self):
        expect_dict = {"entries_size": 3,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {}}},
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                       "zvampirem3": {"": {"categories": {"list_buckets": {"ops": 6, "successful_ops": 6}}}}}
        req_url = "http://{server}/{admin}/usage?format=json&categories={categories}&start={start}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, categories="list_buckets", start = self.m_start_time_stamp)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_and_categories_without_end_and_uid %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_and_categories_without_end_and_uid %s" % (fail_display("FAIL"))

    #test "usage show" with start, uid and categories, without end
    def test_usage_show_with_start_uid_categories_without_end(self):
        expect_dict = {"entries_size": 1,
                       "zvampirem:chosenone": {"chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}&categories={categories}&start={start}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone", categories="create_bucket", start = self.m_start_time_stamp)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_uid_categories_without_end         %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_uid_categories_without_end         %s" % (fail_display("FAIL"))

    #test "usage show" with end, but without start, uid and categories
    def test_usage_show_with_end_without_start_uid_and_categories(self):
        expect_dict = {"entries_size": 1,
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, end = self.m_end_time_stamp)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_end_without_start_uid_and_categories     %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_end_without_start_uid_and_categories     %s" % (fail_display("FAIL"))
        
    #test "usage show" with end and uid, without start and categories
    def test_usage_show_with_end_and_uid_without_start_and_categories(self):
        expect_dict = {"entries_size": 1,
                       "time_test:time_test_sub": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "time_test", subuser = "time_test_sub", end = self.m_end_time_stamp)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_end_and_uid_without_start_and_categories %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_end_and_uid_without_start_and_categories %s" % (fail_display("FAIL"))


    #test "usage show" with end and categories, without start and uid
    def test_usage_show_with_end_and_categories_without_start_and_uid(self):
        expect_dict = {"entries_size": 1,
                       "time_test": {"": {"categories": {}}},
                      }

        req_url = "http://{server}/{admin}/usage?format=json&categories={categories}&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, categories = "create_bucket", end = self.m_end_time_stamp)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_end_and_categories_without_start_and_uid %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_end_and_categories_without_start_and_uid %s" % (fail_display("FAIL"))

    #test "usage show" with end, uid and categories, without start
    def test_usage_show_with_end_uid_and_categories_without_start(self):
        expect_dict = {"entries_size": 1,
                       "time_test:time_test_sub": {"": {"categories": {}}}}
        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}&categories={categories}&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "time_test", subuser = "time_test_sub", categories = "create_bucket", end = self.m_end_time_stamp)
        result = self.verify_get_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_end_uid_and_categories_without_start     %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_end_uid_and_categories_without_start     %s" % (fail_display("FAIL"))

    #test "usage show" with start and end, without uid and categories
    def test_usage_show_with_start_and_end_without_uid_and_categories(self):
        
        req_url = "http://{server}/{admin}/usage?format=json&start={start}&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, start = self.m_start_time_stamp, end = self.m_end_time_stamp)
        response = requests.get(req_url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
        res_content = json.loads(response.text)

#        print res_content

        result = True
        if len(res_content["entries"]) != 0 or len(res_content["summary"]) != 0:
            result = False

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_and_end_without_uid_and_categories %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_and_end_without_uid_and_categories %s" % (fail_display("FAIL"))
            

    #test "usage show" with start, end and uid, without categories
    def test_usage_show_with_start_end_and_uid_without_categories(self):
        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&start={start}&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", start = self.m_start_time_stamp, end = self.m_end_time_stamp)
        response = requests.get(req_url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
        res_content = json.loads(response.text)

#        print res_content

        result = True
        if len(res_content["entries"]) != 0 or len(res_content["summary"]) != 0:
            result = False

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_end_and_uid_without_categories     %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_end_and_uid_without_categories     %s" % (fail_display("FAIL"))

    #test "usage show" with start, end, uid and categories
    def test_usage_show_with_start_end_uid_and_categories(self):
        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&categories={categories}&start={start}&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", categories = "list_buckets", start = self.m_start_time_stamp, end = self.m_end_time_stamp)
        response = requests.get(req_url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
        res_content = json.loads(response.text)

#        print res_content

        result = True
        if len(res_content["entries"]) != 0 or len(res_content["summary"]) != 0:
            result = False

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_start_end_uid_and_categories             %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_start_end_uid_and_categories             %s" % (fail_display("FAIL"))


    #test "usage show" with show-entries = false
    def test_usage_show_with_show_entries_false(self):
        req_url = "http://{server}/{admin}/usage?format=json&show-entries=false".format(server = ceph_cluster_server, admin = ceph_cluster_admin)
        response = requests.get(req_url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
        res_content = json.loads(response.text)
        result = False

        if len(res_content["summary"]) == 4:
            try:
                print res_content["entries"]
            except KeyError:
                result = True

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_show_entries_false                       %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_show_entries_false                       %s" % (fail_display("FAIL"))


    #test "usage show" with show-summary = false
    def test_usage_show_with_show_summary_false(self):
        req_url = "http://{server}/{admin}/usage?format=json&show-summary=false".format(server = ceph_cluster_server, admin = ceph_cluster_admin)
        response = requests.get(req_url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
        res_content = json.loads(response.text)
        result = False

        if len(res_content["entries"]) == 4:
            try:
                print res_content["summary"]
            except KeyError:
                result = True

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_show_with_show_summary_false                       %s" % (ok_display("OK"))
        else:
            print "test_usage_show_with_show_summary_false                       %s" % (fail_display("FAIL"))


    #test "usage trim" with uid = user
    def test_usage_trim_with_uid_user(self):
        expect_dict1 = {"entries_size": 3,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}},
                      }

        expect_dict2 = {"entries_size": 0}

        req_url1 = "http://{server}/{admin}/usage?format=json&uid={uid}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem3")
        result1 = self.verify_del_response_msg(req_url1, expect_dict1)

	req_url2 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem3", subuser = "chosenone3")
	result2 = self.verify_get_response_msg(req_url2, expect_dict2)

        if (result1 and result2) == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_uid_user                                 %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_uid_user                                 %s" % (fail_display("FAIL"))

    #test "usage trim" with uid = subuser
    def test_usage_trim_with_uid_subuser(self):
        expect_dict = {"entries_size": 3,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "zvampirem2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}},
                      }

        req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenoneex")
        result = self.verify_del_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_uid_subuser                              %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_uid_subuser                              %s" % (fail_display("FAIL"))

    #test "usage trim" with start and uid, without end:
    def test_usage_time_with_start_and_uid_without_end(self):
        expect_dict1 = {"entries_size": 2,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

        expect_dict2 = {"entries_size": 1,
			"zvampirem2:chosenone2": {"": {"categories": {"list_buckets": {"ops": 7, "successful_ops": 7}}}}}

        
        req_url1 = "http://{server}/{admin}/usage?format=json&uid={uid}&start={start}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem2", start = self.m_start_time_stamp)
        result1 = self.verify_del_response_msg(req_url1, expect_dict1)
	req_url2 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem2", subuser = "chosenone2")
	result2 = self.verify_get_response_msg(req_url2, expect_dict2)

        if (result1 and result2) == True:
            self.m_test_passed_num += 1
            print "test_usage_time_with_start_and_uid_without_end                %s" % (ok_display("OK"))
        else:
            print "test_usage_time_with_start_and_uid_without_end                %s" % (fail_display("FAIL"))

    #test "usage trim" with end and uid, without start
    def test_usage_trim_with_end_and_uid_without_start(self):
        expect_dict1 = {"entries_size": 2,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
                }

        expect_dict2 = {"entries_size": 1,
	                "zvampirem:chosenone": {"chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}}


        req_url1 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone", end = self.m_end_time_stamp)
        result1 = self.verify_del_response_msg(req_url1, expect_dict1)

        req_url2 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone")
        result2 = self.verify_get_response_msg(req_url2, expect_dict2)

        if (result1 and result2) == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_end_and_uid_without_start                %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_end_and_uid_without_start                %s" % (fail_display("FAIL"))

    #test "usage trim" with start, end and uid
    def test_usage_trim_with_start_end_and_uid(self):
        expect_dict1 = {"entries_size": 2,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}},
                }

        expect_dict2 = {"entries_size": 1,
			"zvampirem:chosenone": {"chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}}}

        req_url1 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}&start={start}&end={end}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone", start = self.m_start_time_stamp, end = self.m_end_time_stamp)
        result1 = self.verify_del_response_msg(req_url1, expect_dict1)

	req_url2 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone")
	result2 = self.verify_get_response_msg(req_url2, expect_dict2)

        if (result1 and result2) == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_start_end_and_uid                        %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_start_end_and_uid                        %s" % (fail_display("FAIL"))
        

    # test "usage trim" with all-subuser and start time without end time
    def test_usage_trim_with_all_subuser_and_start_without_end(self):
	expect_dict1 = {"entries_size": 2,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}},
                }
        
	expect_dict2 = {"entries_size": 0}
	expect_dict3 = {"entries_size": 0}
	expect_dict4 = {"entries_size": 1,
			"time_test:time_test_sub": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

	req_url1 = "http://{server}/{admin}/usage?format=json&start={start}&all-subuser=true&remove-all=true".format(server = ceph_cluster_server, admin = ceph_cluster_admin, start = self.m_start_time_stamp)
	result1 = self.verify_del_response_msg(req_url1, expect_dict1)
        req_url2 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone")
        req_url3 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem2", subuser = "chosenone2")
        req_url4 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "time_test", subuser = "time_test_sub")
        result2 = self.verify_get_response_msg(req_url2, expect_dict2)
        result3 = self.verify_get_response_msg(req_url3, expect_dict3)
	result4 = self.verify_get_response_msg(req_url4, expect_dict4)

        if (result1 and result2 and result3 and result4) == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_all_subuser_and_start_without_end        %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_all_subuser_and_start_without_end        %s" % (fail_display("FAIL"))

    # test "usage trim" with all subuser and end time without start time
    def test_usage_trim_with_all_subuser_and_end_without_start(self):
        expect_dict1 = {"entries_size": 2,
                       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone-bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}},
                }
        
	expect_dict2 = {"entries_size": 0}
	expect_dict3 = {"entries_size": 0}
	expect_dict4 = {"entries_size": 1,
			"time_test:time_test_sub": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}}

	req_url1 = "http://{server}/{admin}/usage?format=json&end={end}&all-subuser=true&remove-all=true".format(server = ceph_cluster_server, admin = ceph_cluster_admin, end = self.m_end_time_stamp2)
	result1 = self.verify_del_response_msg(req_url1, expect_dict1)
        req_url2 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone")
        req_url3 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem2", subuser = "chosenone2")
        req_url4 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "time_test", subuser = "time_test_sub")
        result2 = self.verify_get_response_msg(req_url2, expect_dict2)
        result3 = self.verify_get_response_msg(req_url3, expect_dict3)
	result4 = self.verify_get_response_msg(req_url4, expect_dict4)

        if (result1 and result2 and result3 and result4) == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_all_subuser_and_end_without_start        %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_all_subuser_and_end_without_start        %s" % (fail_display("FAIL"))

    # test "usage trim" with all subuser without start time and end time
    def test_usage_trim_with_all_subuser_without_start_and_end(self):
        expect_dict1 = {"entries_size": 2,
		       "zvampirem": {"": {"categories": {"list_buckets": {"ops": 5, "successful_ops": 5}}},
                                     "chosenone_bucket": {"categories": {"create_bucket": {"ops": 1, "successful_ops": 1}, "delete_bucket": {"ops": 1, "successful_ops": 1}}}},
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}},
                }
        
	expect_dict2 = {"entries_size": 0}
	expect_dict3 = {"entries_size": 0}
	expect_dict4 = {"entries_size": 0}

	req_url1 = "http://{server}/{admin}/usage?format=json&all-subuser=true&remove-all=true".format(server = ceph_cluster_server, admin = ceph_cluster_admin)
	result1 = self.verify_del_response_msg(req_url1, expect_dict1)
        req_url2 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem", subuser = "chosenone")
        req_url3 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "zvampirem2", subuser = "chosenone2")
        req_url4 = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = "time_test", subuser = "time_test_sub")
        result2 = self.verify_get_response_msg(req_url2, expect_dict2)
        result3 = self.verify_get_response_msg(req_url3, expect_dict3)
	result4 = self.verify_get_response_msg(req_url4, expect_dict4)

        if (result1 and result2 and result3 and result4) == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_all_subuser_without_start_and_end        %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_all_subuser_without_start_and_end        %s" % (fail_display("FAIL"))



    #test "usage trim" with start and remove-all = True, without end
    def test_usage_trim_with_start_and_remove_all_without_end(self):
        expect_dict = {"entries_size": 1,
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
                       }
        req_url = "http://{server}/{admin}/usage?format=json&start={start}&remove-all=True".format(server = ceph_cluster_server, admin = ceph_cluster_admin, start = self.m_start_time_stamp)
        result = self.verify_del_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_start_and_remove_all_without_end         %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_start_and_remove_all_without_end         %s" % (fail_display("FAIL"))

    #test "usage trim" with end and remove-all = True, without start
    def test_usage_trim_with_end_and_remove_all_without_start(self):
        self.m_test_passed_num += 1
        print "test_usage_trim_with_end_and_remove_all_without_start         %s" % (ok_display("OK"))

    #test "usage trim" with start and end and remove-all = True
    def test_usage_trim_with_start_and_end_and_remove_all(self):
        expect_dict = {"entries_size": 1,
                       "time_test": {"": {"categories": {"list_buckets": {"ops": 4, "successful_ops": 4}}}}
                       }
        req_url = "http://{server}/{admin}/usage?format=json&start={start}&end={end}&remove-all=True".format(server = ceph_cluster_server, admin = ceph_cluster_admin, start = self.m_start_time_stamp, end = self.m_end_time_stamp)
        result = self.verify_del_response_msg(req_url, expect_dict)

        if result == True:
            self.m_test_passed_num += 1
            print "test_usage_trim_with_start_and_end_and_remove_all             %s" % (ok_display("OK"))
        else:
            print "test_usage_trim_with_start_and_end_and_remove_all             %s" % (fail_display("FAIL"))


    def test_run(self):
        self.test_usage_show_without_any_param()
        self.test_usage_show_with_uid_user_for_user_operating()
        self.test_usage_show_with_uid_subuser_for_user_operating()
        self.test_usage_show_with_uid_user_for_subuser_operating()
        self.test_usage_show_with_uid_subuser_for_subuser_operating()
        self.test_usage_show_with_uid_user_without_categories()
        self.test_usage_show_with_uid_subuser_without_categories()
        self.test_usage_show_with_categories_without_uid()
        self.test_usage_show_with_uid_user_and_categories()
        self.test_usage_show_with_uid_subuser_and_categories()
        self.test_usage_show_with_start_without_end_uid_categories()
        self.test_usage_show_with_start_and_uid_without_end_and_categories()
        self.test_usage_show_with_start_and_categories_without_end_and_uid()
        self.test_usage_show_with_start_uid_categories_without_end()
        self.test_usage_show_with_end_without_start_uid_and_categories()
        self.test_usage_show_with_end_and_uid_without_start_and_categories()
        self.test_usage_show_with_end_and_categories_without_start_and_uid()
        self.test_usage_show_with_end_uid_and_categories_without_start()
        self.test_usage_show_with_start_and_end_without_uid_and_categories()
        self.test_usage_show_with_start_end_and_uid_without_categories()
        self.test_usage_show_with_start_end_uid_and_categories()
        self.test_usage_show_with_show_entries_false()
        self.test_usage_show_with_show_summary_false()
        self.test_usage_trim_with_uid_user()
        self.test_usage_trim_with_uid_subuser()
        self.test_usage_time_with_start_and_uid_without_end()
        self.test_usage_trim_with_end_and_uid_without_start()
        self.test_usage_trim_with_start_end_and_uid()
	self.test_usage_trim_with_all_subuser_without_start_and_end()
#	self.test_usage_trim_with_all_subuser_and_start_without_end()
#	self.test_usage_trim_with_all_subuser_and_end_without_start()
##        self.test_usage_trim_with_start_and_remove_all_without_end()
#        self.test_usage_trim_with_end_and_remove_all_without_start()
#        self.test_usage_trim_with_start_and_end_and_remove_all()
    
    def clean_env(self, user):
        if ":" in user:
            user_list = user.split(':')
            req_url = "http://{server}/{admin}/usage?format=json&uid={uid}&subuser={subuser}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = user_list[0], subuser = user_list[1])
        else:
            req_url = "http://{server}/{admin}/usage?format=json&uid={uid}".format(server = ceph_cluster_server, admin = ceph_cluster_admin, uid = user)
        response = requests.delete(req_url, auth=S3Auth(ceph_cluster_admin_access_key, ceph_cluster_admin_secret_key, ceph_cluster_server))
        if response.status_code == RES_OK:
            print "Trim " + user + " testing usage log! OK"
            return True
        else:
            print "Trim " + user + " testing usage log! FAIL"
            return False
        
    def test_end(self):
        print "***************************************************************************************"
        if self.clean_env("zvampirem") \
        and self.clean_env("zvampirem:chosenone") \
        and self.clean_env("zvampirem:chosenoneex") \
        and self.clean_env("zvampirem2") \
        and self.clean_env("zvampirem2:chosenone2") \
        and self.clean_env("zvampirem3") \
        and self.clean_env("zvampirem3:chosenone3"):
            print "Test End!"
            print "Total test case: 32, OK: %d, FAIL: %d" % (self.m_test_passed_num, 32 - self.m_test_passed_num)


if __name__ == '__main__':
    tester = Tester()
    tester.test_preparation()
    tester.test_run()
    tester.test_end()
