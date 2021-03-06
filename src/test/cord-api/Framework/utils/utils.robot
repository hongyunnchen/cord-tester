*** Settings ***
Documentation    Library for various utilities
Library           SSHLibrary
Library           HttpLibrary.HTTP
Library           String
Library           DateTime
Library           Process
Library           Collections
Library           RequestsLibrary
#Library           ${CURDIR}/readProperties.py
#Resource          ${CURDIR}/utils.py

*** Keywords ***
Run Command On Remote System
    [Arguments]    ${system}    ${cmd}    ${user}=${VM_USER}    ${pass}=${VM_PASS}    ${prompt}=$    ${prompt_timeout}=60s    ${use_key}=False
    [Documentation]    SSH's into a remote host, executes command, and logs+returns output
    BuiltIn.Log    Attempting to execute command "${cmd}" on remote system "${system}"
    BuiltIn.Log    ${password}
    ${conn_id}=    SSHLibrary.Open Connection    ${system}    prompt=${prompt}    timeout=${prompt_timeout}
    Run Keyword If    '${use_key}' == 'False'    SSHLibrary.Login    ${user}    ${pass}    ELSE    SSHLibrary.Login With Public Key    ${user}    %{HOME}/.ssh/${SSH_KEY}    any
    #SSHLibrary.Login    ${user}    ${pass}
    ${output}=    SSHLibrary.Execute Command    ${cmd}
    SSHLibrary.Close Connection
    Log    ${output}
    [Return]    ${output}

Execute Command on CIAB Server in Specific VM
    [Arguments]    ${system}    ${vm}    ${cmd}    ${user}=${VM_USER}    ${password}=${VM_PASS}    ${prompt}=$    ${use_key}=True
    [Documentation]    SSHs into ${HOST} where CIAB is running and executes a command in the Prod Vagrant VM where all the containers are running
    ${conn_id}=    SSHLibrary.Open Connection    ${system}    prompt=${prompt}    timeout=300s
    Run Keyword If    '${use_key}' == 'False'    SSHLibrary.Login    ${user}    ${pass}    ELSE    SSHLibrary.Login With Public Key    ${user}    %{HOME}/.ssh/${SSH_KEY}    any
    SSHLibrary.Write    ssh ${vm}
    SSHLibrary.Read Until Prompt
    SSHLibrary.Write    ${cmd}
    ${output}=    SSHLibrary.Read Until Prompt
    SSHLibrary.Close Connection
    ${output}=    Get Line    ${output}    0
    [Return]    ${output}

Execute Command on Compute Node in CIAB
    [Arguments]    ${system}    ${hostname}    ${cmd}    ${user}=${VM_USER}    ${password}=${VM_PASS}    ${prompt}=$    ${use_key}=True
    [Documentation]    SSHs into ${HOST} where CIAB is running and executes a command in the Prod Vagrant VM where all the containers are running
    ${conn_id}=    SSHLibrary.Open Connection    ${system}    prompt=${prompt}    timeout=300s
    Run Keyword If    '${use_key}' == 'False'    SSHLibrary.Login    ${user}    ${pass}    ELSE    SSHLibrary.Login With Public Key    ${user}    %{HOME}/.ssh/${SSH_KEY}    any
    SSHLibrary.Write    ssh prod
    SSHLibrary.Read Until Prompt
    SSHLibrary.Write    ssh root@${hostname}
    SSHLibrary.Read Until    \#
    SSHLibrary.Write    ${cmd}
    ${output}=    SSHLibrary.Read Until   \#
    SSHLibrary.Close Connection
    [Return]    ${output}

Get Docker Container ID
    [Arguments]    ${system}    ${container_name}    ${user}=${USER}    ${password}=${PASSWD}
    [Documentation]    Retrieves the id of the requested docker container running inside given ${HOST}
    ${container_id}=    Execute Command on CIAB Server in Specific VM    ${system}    prod    docker ps | grep ${container_name} | awk '{print $1}'    ${user}    ${password}
    Log    ${container_id}
    [Return]    ${container_id}

Get Docker Logs
    [Arguments]    ${system}    ${container_id}    ${user}=${USER}    ${password}=${PASSWD}    ${prompt}=prod:~$
    [Documentation]    Retrieves the id of the requested docker container running inside given ${HOST}
    ##In Ciab, all containers are run in the prod vm so we must log into that
    ${conn_id}=    SSHLibrary.Open Connection    ${system}    prompt=$    timeout=300s
    SSHLibrary.Login With Public Key    ${USER}    %{HOME}/.ssh/${SSH_KEY}    any
    #SSHLibrary.Login    ${HOST_USER}    ${HOST_PASSWORD}
    SSHLibrary.Write    ssh prod
    SSHLibrary.Read Until    ${prompt}
    SSHLibrary.Write    docker logs -t ${container_id}
    ${container_logs}=    SSHLibrary.Read Until    ${prompt}
    SSHLibrary.Close Connection
    Log    ${container_logs}
    [Return]    ${container_logs}