#!/usr/bin/python

import requests
import json
import base64
import ConfigParser

def processStorageCenter(storagecenter):
    sysdata = {}
    sysdata.update({'name': storagecenter['name']})
    sysdata.update({'manufacturer': 'Dell Inc.'})
    sysdata.update({'os': 'Storage Center'})
    sysdata.update({'osversion': storagecenter['version']})
    sysdata.update({'serial_no': storagecenter['serialNumber']})
    sysdata.update({'type': 'cluster'})
    return sysdata
    
def processController(controller):
    sysdata = {}
    sysdata.update({'name': controller['domainName']})
    sysdata.update({'serial_no': controller['hardwareSerialNumber']})
    sysdata.update({'manufacturer': 'Dell Inc.'})
    sysdata.update({'os': 'Storage Center'})
    sysdata.update({'osversion': controller['version']})
    
    if 'SC4020' in controller['model']:
        sysdata.update({'hardware': 'Dell Storage SC4020 Controller'})
        sysdata.update({'cpucount': 1})
        sysdata.update({'cpucore': 4})
        sysdata.update({'cpupower': 2.5})
        sysdata.update({'memory': 16})
        sysdata.update({'type': 'blade'})
        sysdata.update({'blade_host': controller['scName'] + ' - Chassis'})
        sysdata.update({'slot_no': controller['canisterId']})
        
    elif 'SC8000' in controller['model']:
        sysdata.update({'hardware': 'Dell Storage SC8000 Controller'})
        sysdata.update({'cpucount': 2})
        sysdata.update({'cpucore': 6})
        sysdata.update({'cpupower': 2.5})
        sysdata.update({'type': 'physical'})
        
        #the SC8000 base model has 16 GB of RAM, but there is a 64 GB upgrade
        #if we see more than 16 GB of RAM available assume its the 64 GB version
        if int(controller['availableMemory'].split(' ')[0]) > 16000000000:
            sysdata.update({'memory': 64})
        else:
            sysdata.update({'memory': 16})
            
    else:
        print 'Unknown controller model discovered'
    
    return sysdata

def processEnclosure(enclosure):
    sysdata = {}       
    sysdata.update({'name': enclosure['scName'] + ' - ' + enclosure['instanceName']})
        
    if 'SC4020' in enclosure['model']:
        #This is the enclosure built into the base SC4020 chassis so needs special handling for the name
        sysdata = {}
        sysdata.update({'name': enclosure['scName'] + ' - Chassis'})
        sysdata.update({'hardware': 'Dell Storage SC4020 Chassis'})
        sysdata.update({'is_it_blade_host': 'yes'})
    elif 'SC200' in enclosure['model']:
        sysdata.update({'hardware': 'Dell Storage SC200 Expansion Enclosure'})
    elif 'SC220' in enclosure['model']:
        sysdata.update({'hardware': 'Dell Storage SC220 Expansion Enclosure'})
    else:
        sysdata.update({'hardware': enclosure['model']})
            
    sysdata.update({'serial_no': enclosure['serviceTag']})
    sysdata.update({'manufacturer': 'Dell Inc.'})
    sysdata.update({'type': 'physical'})
        
    return sysdata

def main():
    config = ConfigParser.ConfigParser()
    config.readfp(open('dellstorage-device42.cfg'))
    dellusername = config.get('dell','username')
    dellpassword = config.get('dell','password')
    dellUri = config.get('dell','baseUri')
    d42username = config.get('device42','username')
    d42password = config.get('device42','password')
    device42Uri = config.get('device42','baseUri')
    dsheaders = {'Authorization': 'Basic ' + base64.b64encode(d42username + ':' + d42password), 'Content-Type': 'application/x-www-form-urlencoded'}

    s=requests.Session()
    s.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json', 'x-dell-api-version': '2.2'})
    s.verify=False #disable once we get a real cert

    dellauth = {'Authorization': 'Basic ' + base64.b64encode(dellusername + ':' + dellpassword), 'Content-Type': 'application/json', 'x-dell-api-version': '2.2'}
    r=s.post(dellUri+'/ApiConnection/Login','{}',headers=dellauth)

    storagecenters=s.get(dellUri+'/StorageCenter/StorageCenter')
    for storagecenter in storagecenters.json():
        devicesInCluster=[]   
        storagecentersysdata = processStorageCenter(storagecenter)
        
        #do enclosures before controllers (in case one is a controller chassis)
        enclosures=s.get(dellUri+'/StorageCenter/StorageCenter/'+storagecenter['instanceId']+'/EnclosureList')
        disks=s.get(dellUri+'/StorageCenter/StorageCenter/'+storagecenter['instanceId']+'/DiskList')
        for enclosure in enclosures.json(): 
            enclosuresysdata = processEnclosure(enclosure)
            devicesInCluster.append(enclosure['name'])
            r=requests.post(device42Uri+'/device/',data=enclosuresysdata,headers=dsheaders)
         
        controllers=s.get(dellUri+'/StorageCenter/StorageCenter/'+storagecenter['instanceId']+'/ControllerList')
        for controller in controllers.json():
            controllersysdata = processController(controller)
            devicesInCluster.append(controllersysdata['name'])
            #ports=s.get(dellUri+'/StorageCenter/ScController/'+controller['instanceId']+'/PhysicalControllerPortList')
            r=requests.post(device42Uri+'/device/',data=controllersysdata,headers=dsheaders)
        
        storagecentersysdata.update({'devices_in_cluster': ','.join(devicesInCluster)})
        r=requests.post(device42Uri+'/device/',data=storagecentersysdata,headers=dsheaders)
        
    r=s.post(dellUri+'/ApiConnection/Logout','{}')

    return

if __name__ == '__main__': 
    main()
