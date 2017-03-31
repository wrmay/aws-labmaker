#
# Copyright (c) 2015-2016 Pivotal Software, Inc. All Rights Reserved.
#
# note: this is python3!
import jinja2
import json
import os
import os.path
import shutil
import subprocess
import sys
import threading
import time
import tempfile

#args should be a list
def runListQuietly(args):
    p = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    output = p.communicate()
    if p.returncode != 0:
        raise Exception('"{0}" failed with the following output: {1}'.format(' '.join(list(args)), output[0]))

def runQuietly(*args):
    runListQuietly(list(args))

def runRemote(sshKeyPath, user, host, *args):
    prefix = ['ssh', '-o','StrictHostKeyChecking=no',
                        '-t',
                        '-i', sshKeyPath,
                        '{0}@{1}'.format(user, host)]

    subprocess.check_call(prefix + list(args))


def runRemoteQuietly(sshKeyPath, user, host, *args):
    prefix = ['ssh', '-o','StrictHostKeyChecking=no',
                        '-t',
                        '-i', sshKeyPath,
                        '{0}@{1}'.format(user, host)]

    runListQuietly( prefix + list(args))

def renderTemplate(directory, templateFile, context):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(directory))
    env.trim_blocks = True
    env.lstrip_blocks = True
    outputFile = templateFile[:-4]
    template = env.get_template(templateFile)
    with open(os.path.join(directory,outputFile), 'w') as outf:
        template.stream(context).dump(outf)


# def runRemoteQuietly(sshKeyPath, user, host, *args):
#     newargs = ['ssh', '-o', 'StrictHostKeyChecking=no',
#                '-t',
#                '-i', sshKeyPath,
#                user + '@' + host] + list(args)
#
#     cmd = ' '.join(newargs)
#
#     p = subprocess.Popen(newargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
#     output = p.communicate()
#     if p.returncode != 0:
#         msg = '"' + cmd + '" failed with the following output: \n\t' + output[0]
#         raise Exception(msg)

def renderTemplatesInDir(context,dirname):
    #print('rendering templates in {0}'.format(dirname))
    for templateFile in os.listdir(dirname):
        if os.path.isdir(os.path.join(dirname,templateFile)):
            renderTemplatesInDir(context, os.path.join(dirname, templateFile))

        elif templateFile.endswith('.tpl'):
            renderTemplate(dirname, templateFile, context)


if __name__ == '__main__':
    assert sys.version_info >= (3,0)

    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    configDir = os.path.join(here,'config')
    configFile = os.path.join(configDir,'env.json')
    templateDir = os.path.join(here,'templates')
    setupTasksDir = os.path.join(here,'setuptasks')
    storageMapFile = os.path.join(here,'aws_runtime_storage.json')
    instanceMapFile = os.path.join(here,'aws_runtime.json')

    #read the environment file
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(configDir))
    with open(configFile, 'r') as contextFile:
        context = json.load(contextFile)


    print ("current directory:"+os.getcwd())
    
    with open(instanceMapFile,'r') as f:
        ipTable = json.load(f)

    serverNum = -1
    for server in context['Servers']:
        serverName = server['Name']
        ip = ipTable[serverName]
        server['PublicIpAddress'] = ip
        serverNum += 1
        installationNum = -1
        for installation in server['Installations']:
            installationNum += 1
            context['ServerNum'] = serverNum
            context['InstallationNum'] = installationNum
            installationDir = os.path.join(setupTasksDir,installation['Name'])

            # copy the additonal files into the installation dir
            additionalsDir = None
            if 'AdditionalFiles' in installation:
                additionalsDir = tempfile.mkdtemp()
                for addFile in installation['AdditionalFiles']:
                    source = os.path.join(here,addFile)
                    if os.path.isfile(source):
                        shutil.copy(source, additionalsDir)
                    elif os.path.isdir(source):
                        # put the CONTENTS of the named dir into the tempDir
                        for thing in os.listdir(source):
                            thingpath = os.path.join(source, thing)
                            if os.path.isfile(thingpath):
                                shutil.copy(thingpath,additionalsDir)
                            else:
                                shutil.copytree(thingpath, os.path.join(additionalsDir,thing))

                    else:
                        print('Additional file "{0}" not found. Continuing.'.format(addFile))

            renderTemplatesInDir(context, installationDir)

            runQuietly('rsync', '-avz','--delete',
                '-e' ,'ssh -o StrictHostKeyChecking=no -i {0}'.format(context['SSHKeyPath']),
                installationDir + '/', server['SSHUser'] + '@' + ip + ':/tmp/setup')

            if additionalsDir is not None:
                runQuietly('rsync', '-avz',
                    '-e' ,'ssh -o StrictHostKeyChecking=no -i {0}'.format(context['SSHKeyPath']),
                    additionalsDir + '/', server['SSHUser'] + '@' + ip + ':/tmp/setup')

                shutil.rmtree(additionalsDir)


            runRemote(context['SSHKeyPath'], server['SSHUser'], ip,
                      'sudo', 'python','/tmp/setup/setup.py')

            runRemoteQuietly(context['SSHKeyPath'], server['SSHUser'], ip,
                     'rm','-rf', '/tmp/setup')
