#!/bin/env python

# command line tool to run shell commands, list hosts via tags, etc

from yahoo.contrib.mep.aws_helper import ssm
from yahoo.contrib.mep.aws_splunk import athens
from pprint import pprint
import argparse
import requests
import json
import time
import sys

# 2 different methods to obtain temp creds

def get_creds_sia(region):
    athens_domain = aws_domain = ''
    athens_service = ''
    aws_role = ''

    token = athens.get_ntoken(athens_domain, athens_service)
    athens.get_aws_zts_pem()
    creds = athens.fetch_aws_temp_creds(token, aws_domain, aws_role)
    creds['region'] = region

    return creds

def get_creds_zts(region):
    athens_domain = ''
    aws_role = ''

    zts_url = 'https://<ZTS URL>:4443/zts/v1/domain/%s/role/%s/creds' % (athens_domain, aws_role)
    priv_key = 'path to priv key'
    cert = 'path to cert'

    creds = requests.get(zts_url, cert=(cert, priv_key))
    creds = json.loads(creds.text)
    creds['region'] = region

    return creds

def get_cmd_status(id):
    cmd = aws.get_command_status(id)
    return cmd['Commands'][0]['Status']

def get_instance_ids(instance_list):
    instance_ids = []
    for i in instance_list['Tags']:
        if i['ResourceType'] == 'instance':
            instance_ids.append(i['ResourceId'])

    return instance_ids

def run_command(key, value, cmd):
    request = get_instances(key, value)
    instance_ids = []
    for i in request:
        instance_ids.append(i)

    aws.run_command(instance_ids, cmd)

def get_instances(key, value):
    instances = aws.get_by_tags(aws.build_filter('tag:%s' % key, value))
    
    running_instances = {}
    for i in instances['Tags']:
        if i['ResourceType'] == 'instance':
            r = aws.query_instance([i['ResourceId']])
            if r['Reservations'][0]['Instances'][0]['State']['Name'] == 'running':
                public_hostname =  r['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicDnsName']
                instance_id =  r['Reservations'][0]['Instances'][0]['InstanceId']
                running_instances[instance_id] = public_hostname

    return running_instances

# parse cmd line args
parser = argparse.ArgumentParser()

# add subparser for sub commands
subparsers = parser.add_subparsers(dest='parser_name',
                                   title='sub commands')

# lists instances
list_ec2 = subparsers.add_parser('list', help='Lists ec2 instances')
list_ec2.add_argument('--region')
list_ec2.add_argument('--tag')

# run shell commands
run_shell = subparsers.add_parser('run_shell', help='Run shell commands')
run_shell.add_argument('--cmd')
run_shell.add_argument('--region')
run_shell.add_argument('--tag')

instance_ids    = []
args            = parser.parse_args()
region          = args.region
parser_name     = args.parser_name
tag             = args.tag

# new aws obj
#aws = ssm.Runshell(region = region)
aws = ssm.Runshell(get_creds_sia(region))
 
(key, value) = tag.split(':')

if parser_name == 'list':
    instances = get_instances(key, value)
    for i in instances:
        print(instances[i])
elif parser_name == 'run_shell':
    cmd = args.cmd
    run_command(key, value, cmd)
