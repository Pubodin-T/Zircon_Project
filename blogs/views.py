from django.shortcuts import render
from .models import Drop_sim
from .models import Launch_site
from datetime import datetime
import re
import math
import requests
import json
from sgp4.api import Satrec
from sgp4.api import jday
from sgp4.api import SGP4_ERRORS
from sgp4.api import days2mdhms
# Create your views here.
def homePageView(request):
   
    return render(request, "index.html")

def index(request):
    # Order by Decay Epoch Date
    reentry_dates = []
    datas = Drop_sim.objects.all().order_by('-decay_epoch')
    for data in datas:
        line_split = data.dataset.split('\r\n')
        reentry_date = line_split[-1].split(" ")[0]
        reentry_time = line_split[-1].split(" ")[1]
        x = datetime(int(reentry_date.split("/")[0]), int(reentry_date.split("/")[1]), int(reentry_date.split("/")[2]),int(reentry_time.split(":")[0]),int(reentry_time.split(":")[1]),int(reentry_time.split(":")[2][:2]))
        reentry_dates.append(x.strftime("%d %b %Y , %H:%M:%S UTC"))
    context = {
        'zip_datas': zip(datas, reentry_dates),
    }
    return render(request, "select_obj.html",context)

def match(request, objid=None):
    # then do whatever you want with your params
    reentry_dates = []
    datas = Drop_sim.objects.all().order_by('-decay_epoch')
    for data in datas:
        line_split = data.dataset.split('\r\n')
        reentry_date = line_split[-1].split(" ")[0]
        reentry_time = line_split[-1].split(" ")[1]
        x = datetime(int(reentry_date.split("/")[0]), int(reentry_date.split("/")[1]), int(reentry_date.split("/")[2]),int(reentry_time.split(":")[0]),int(reentry_time.split(":")[1]),int(reentry_time.split(":")[2][:2]))
        reentry_dates.append(x.strftime("%d %b %Y , %H:%M:%S UTC"))





    norad_id = objid
    data = Drop_sim.objects.get(norad_id=norad_id)
    print("Request ObjectID : " + str(objid))
    line_split = data.dataset.split('\r\n')
    date = []
    velocity = []
    latitude = []
    longitude = []
    height = []
    uncertainty = data.uncertainty.split('\r\n')
    uct_lat = []
    uct_lon = []
    uct_alt = []


    for i in line_split:
        #print(i.split(','))
        splited = i.split(',')
        if len(splited) >= 9 :
            if float(splited[7]) >= 0 :
                date.append(splited[0].replace('/', '-').replace(' ', 'T') + "Z")
                velocity.append(math.sqrt(pow(float(splited[4]), 2)+ pow(float(splited[5]), 2)+ pow(float(splited[6]), 2)))
                height.append(float(splited[7]))
                latitude.append(float(splited[8]))
                longitude.append(float(splited[9]))

    for k in uncertainty:
        splited = k.split(',')
        if len(splited) >= 9 :
            #date.append(splited[0].replace(' ', 'T') + "Z")
            uct_alt.append(0)
            uct_lat.append(float(splited[8]))
            uct_lon.append(float(splited[9]))
    
    context = {
        'zip_datas': zip(datas, reentry_dates),
        'totaldata':len(date),
        'data':data ,
        'date':date , 
        'velocity':velocity ,
        'height':height , 
        'latitude':latitude , 
        'longitude':longitude , 
        'uct_lon':uct_lon, 
        'uct_lat':uct_lat, 
        'uct_alt':uct_alt 
    }
    print("Success Request")
    return render(request, "drop.html",context)

def MapView(request):
    data_lst = Launch_site.objects.all()

    context = {
        "data" : data_lst,
    }
     
    return render(request, "map.html", context )

def UTM1View(request):
    return render(request,"UTM1.html")

def UTM2View(request):
    return render(request,"UTM2.html")

def SGP4_120km(tle1,tle2):
    satellite = Satrec.twoline2rv(tle1, tle2)
    month, day, hour, minute, second = days2mdhms(int(tle1[18:20]),float(tle1[20:32]))
    i=0
    altitude=9999
    year=int('20'+tle1[18:20])
    epoch=[year,month,day,hour,minute,second]
    #print('Epoch='+str([year,month,day,hour,minute,second]))
    #print(SGP4_ERRORS)
    while altitude>120:
        hour=hour+i
        if hour>23:
            hour=0
            day=day+1
        if (month==1 or month==3 or month==5 or month==7 or month==8 or month==10 or month==12) and day>31:
            day=1
            month=month+1
        if (month==4 or month==6 or month==9 or month==11) and day>30:
            day=1
            month=month+1
        if month==2 and day>28 and year%4!=0:
            day=1
            month=month+1
        if month==2 and day>29 and year%4==0:
            day=1
            month=month+1
        if month>12:
            month=1
            year=year+1
        i=1
        jd, fr = jday(year, month, day, hour, minute, second)
        e, r, v = satellite.sgp4(jd, fr)
        #r=position v=velocity in cartisien coordianate
        altitude=math.sqrt(r[0]**2+r[1]**2+r[2]**2)-6371
        if e==1:
            return [year,month, day, hour, minute, second],epoch, altitude,r,v,e
        if year>2100:
            e=7
            return [year,month, day, hour, minute, second],epoch, altitude,r,v,e
        
    return [year,month, day, hour, minute, second],epoch, altitude,r,v,e

def Spacetrack_to_TLE():
    class MyError(Exception):
        def __init___(self,args):
            Exception.__init__(self,"my exception was raised with arguments {0}".format(args))
            self.args = args

    # See https://www.space-track.org/documentation for details on REST queries
    # the "Find Starlinks" query searches all satellites with NORAD_CAT_ID > 40000, with OBJECT_NAME matching STARLINK*, 1 line per sat
    # the "OMM Starlink" query gets all Orbital Mean-Elements Messages (OMM) for a specific NORAD_CAT_ID in JSON format

    uriBase                = "https://www.space-track.org"
    requestLogin           = "/ajaxauth/login"
    requestCmdAction       = "/basicspacedata/query" 
    requestFindStarlinks   = "/class/tle_latest/NORAD_CAT_ID/> 40000/ORDINAL/1/perigee/<200/EPOCH/>now-10/format/json/orderby/EPOCH%20desc"
    requestOMMStarlink1    = "/class/tle_latest/NORAD_CAT_ID/"
    requestOMMStarlink2    = "/orderby/EPOCH%20desc/format/3le"

    # Parameters to derive apoapsis and periapsis from mean motion (see https://en.wikipedia.org/wiki/Mean_motion)

    GM = 398600441800000.0
    GM13 = GM ** (1.0/3.0)
    MRAD = 6378.137
    PI = 3.14159265358979
    TPI86 = 2.0 * PI / 86400.0

    # ACTION REQUIRED FOR YOU:
    #=========================
    # Provide a config file in the same directory as this file, called SLTrack.ini, with this format (without the # signs)
    # [configuration]
    # username = XXX
    # password = YYY
    # output = ZZZ
    #
    # ... where XXX and YYY are your www.space-track.org credentials (https://www.space-track.org/auth/createAccount for free account)
    # ... and ZZZ is your Excel Output file - e.g. starlink-track.xlsx (note: make it an .xlsx file)

    # Use configparser package to pull in the ini file (pip install configparser)
    # config = configparser.ConfigParser()
    # config.read("C:/Users/Apirak Oulis/Desktop/Internship/Config.txt")
    # configUsr = config.get("configuration","username")
    # configPwd = config.get("configuration","password")
    # configOut = config.get("configuration","output")
    username = "62010711@kmitl.ac.th"
    password = "Oat1200101876013"
    siteCred = {'identity': username, 'password': password}
    
    # use requests package to drive the RESTful session with space-track.org
    with requests.Session() as session:
        # run the session in a with block to force session to close if we exit

        # need to log in first. note that we get a 200 to say the web site got the data, not that we are logged in
        resp = session.post(uriBase + requestLogin, data = siteCred)
        if resp.status_code != 200:
            raise MyError(resp, "POST fail on login")
        # this query picks up all Starlink satellites from the catalog. Note - a 401 failure shows you have bad credentials 
        try:
            resp = session.get(uriBase + requestCmdAction + requestFindStarlinks)
        
            if resp.status_code != 200:
                print(resp)
                raise MyError(resp, "GET fail on request for all objects")
        

            # use the json package to break the json formatted response text into a Python structure (a list of dictionaries)
            retData = json.loads(resp.text)
            satCount = len(retData)
            print(len(retData))
            satIds = []
            for e in retData:
                # each e describes the latest elements for one Starlink satellite. We just need the NORAD_CAT_ID 
                catId = e['NORAD_CAT_ID']
                satIds.append(catId)

            # using our new list of Starlink satellite NORAD_CAT_IDs, we can now get the OMM message
            maxs = 1
            
            tle1=[]
            tle2=[]
            #At first, program stopped when it detected error
            #Solution, try-except 
            for s in satIds:
                try:
                    resp = session.get(uriBase + requestCmdAction + requestOMMStarlink1 + s + requestOMMStarlink2)
                    if resp.status_code != 200:
                        # If you are getting error 500's here, its probably the rate throttle on the site (20/min and 200/hr)
                        # wait a while and retry
                        #print(resp)
                        
                        raise MyError(resp, "GET fail on request for object " + s)
                    else:
                        """ print((resp.text.split("\n"))[1])
                        print((resp.text.split("\n"))[2])
                        print() """
                        tle1.append((resp.text.split("\n"))[1])
                        tle2.append((resp.text.split("\n"))[2])
                except:
                    #print('ERROR')
                    continue

                # the data here can be quite large, as it's all the elements for every entry for one Starlink satellite
                
                #print(retData[0])
        
            
        except:
                print('Error detected')
                tle1=[]
                tle2=[] 

    return(tle1,tle2)

def TableCoordView(request):
     #Assign TLE
    tle1,tle2=Spacetrack_to_TLE()
    
    #SGP4 propagation
    #create list for every error condition
    #Error0 = no error
    #Error1-5 = SGP4 error
    #Error6 = negative altitude
    #Error7 = diverge

    CoordLst=[]
    speedLst=[]
    idLst=[]
    timeLst=[]
    time_idLst=[]
    altLst=[]
    epochError0=[]
    coordError0=[]
    speedError0=[]
    epochLst=[]
    
    idLstError1=[]         
    timeLstError1=[] 
    altLstError1=[]
    epochError1=[]        
    idLstError7=[]         
    idLst_negativeAlt=[]
    timeLst_negativeAlt=[]
    epochNegativeAlt=[]
    altLst_negativeAlt=[]
    ErrorLst=[]
    idLstError_other=[]
    timeLstError_other=[]
    for i in range (len(tle1)):
        time,epoch_time,altitude,coord,speed,ErrorCheck=SGP4_120km(tle1[i],tle2[i])
        ErrorLst.append(ErrorCheck)
        CoordLst.append(coord)
        speedLst.append(speed)
        epochLst.append(epoch_time)
        if ErrorCheck==0:
            #print(time)
            idLst.append(i)
            timeLst.append(time)
            time_id=time.copy()
            time_id.append(i)
            
            time_idLst.append(time_id)
            
            altLst.append(altitude)
            epochError0.append(epoch_time)
            coordError0.append(coord)
            speedError0.append(speed)
        elif ErrorCheck==1:
            idLstError1.append(i)
            timeLstError1.append(time)
            altLstError1.append(altitude)
            epochError1.append(epoch_time)
            
            """
            print(tle1[i])
            print(tle2[i])
            """
        elif ErrorCheck==7:
            idLstError7.append(i)
            
        elif ErrorCheck==6:
            idLst_negativeAlt.append(i)
            timeLst_negativeAlt.append(time)
            altLst_negativeAlt.append(altitude)
            epochNegativeAlt.append(epoch_time)
        else:
            idLstError_other.append(i)
            timeLstError_other.append(time)
    
    #sorting error0 object by time
    sort_time_idLst=sorted(time_idLst)
    tle=[]
    tle1Lst=[]
    tle2Lst=[]
    sort_coordLst=[]
    sort_speedLst=[]
    
    id_data_Lst=[]
    for i in range (len(idLst)):
        n=sort_time_idLst[i][6]
        tle1Lst.append(tle1[n])
        tle2Lst.append(tle2[n])
        sort_coordLst.append(CoordLst[n])
        sort_speedLst.append(speedLst[n])
        
    for i in range (len(idLst)):
        id_data=[]
        id_data.append(tle1Lst[i])
        id_data.append(tle2Lst[i])
        id_data.append(sort_time_idLst[i])
        id_data.append(sort_coordLst[i])
        id_data.append(sort_speedLst[i])
        id_data_Lst.append(id_data)
    
    context = {
        
        "data2" : id_data_Lst,
    }

    #template = loader.get_template('tablecoord.html')
    return render(request,"tablecoord.html",context)