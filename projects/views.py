#   Copyright 2009, Adam Christian (adam@adamchristian.com) and Slide, Inc.
#	
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the .appendLicense.
#   You may obtain a copy of the License at
#	
#           http://www.apache.org/licenses/LICENSE-2.0
#	
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# Create your views here.
from django.http import Http404,HttpResponseRedirect,HttpResponse
from django.shortcuts import render_to_response
from couchdb.client import ResourceNotFound
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from django.template import RequestContext
from testmill.projects.models import Server, Application
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
import urllib2
import feedparser
import couchdb

# These servers aren't necessary they just enhance the experience
# Access all the defined servers from the DB

try:
    TICKET = Server.objects.get(name="TICKET").path
    #print "Using TICKET Server", TICKET
except:
    TICKET = ''
    
try:
    SOURCE = Server.objects.get(name="SOURCE").path
    #print "Using SOURCE Server", SOURCE
except:
    SOURCE = ''

try:
    HUDSON = Server.objects.get(name="HUDSON").path
    #print "Using HUDSON Server", HUDSON
except:
    HUDSON = ''

# First try to get the couch settings from the DB
# if that doesn't work, use the string from settings.py
try:
    COUCHDB_PATH = Server.objects.get(name="COUCHDB").path
except:
   COUCHDB_PATH = getattr(settings,'COUCHDB_SERVER') 

# See if we can connect to the COUCHDB instance
try:
    COUCHDB = couchdb.Server(COUCHDB_PATH)
    len(COUCHDB)
except:
    raise Exception, "We need to be able to connect to a couchDB server, edit settings.py COUCHDB_SERVER variable, or couchDB on localhost default port."

# Make sure we have a db in couch
try:
    docs = COUCHDB['testmill']
except:
    COUCHDB.create('testmill')

# index summary page
@login_required
def index(request):
    
    if not request.user.is_authenticated():
         return HttpResponseRedirect('/accounts/login')
    
    else:
        docs = COUCHDB['testmill']
        active = len(docs);
        couch = COUCHDB
        ticket = TICKET
        hudson = HUDSON
    
        return render_to_response('projects/index.html', {'active':active, 'couch':couch, 'ticket':ticket, 'hudson':hudson})

#helper function: build the json to display all test projects of an app type
def build_app_dict(app_name):
    docs = COUCHDB['testmill']

    func_str = "function(doc) { if (doc.app == '"+app_name+"'){ emit(null, doc);}}"
    results = docs.query(func_str)
      
    #define the object of the sidebar
    p_dict = {}
    p_dict['text'] = '<img src="/static/js/jquery-ui-1.7.2.custom/css/images/folder.gif" />'+app_name.title()
    p_dict['expanded'] = False
    p_dict['children'] = []

    #build children
    for r in results:
        child = {
            'text':'<img src="/static/js/jquery-ui-1.7.2.custom/css/images/file.gif" /><a style="font-size:11px" href="/projects/doc/'+r.id+'">'+r.value['name']+'</a>',
            'id':r.id,
            'leaf':True,
            }
        p_dict['children'].append(child)
           
    #return the dictionary
    return p_dict


@login_required
def tree(request):
  
    apps_lists = []  
    #build a display for each application
    for app in Application.objects.all():
        apps_lists.append(build_app_dict(app.name))

    json = simplejson.dumps(apps_lists)
    return HttpResponse(json)

#Ajax delete a test case from the grid UI
@login_required
def delete_case(request):
    id = request.POST['id']
    docs = COUCHDB['testmill']
    doc = docs[id]
    
    case_id = request.POST['case_id']
    
    removed = False
    for case in doc['.cases']:
        if case['id'] == case_id:
            doc['.cases'].remove(case)
            removed = True
            docs[id] = doc
           
    return HttpResponse(removed)

#Ajax saving of a changed test case in the grid UI
@login_required
def save_cases(request):
    id = request.GET['id']
    docs = COUCHDB['testmill']
    doc = docs[id]
        
    try:
        l = len(doc['.cases'])
    except:
        doc['.cases'] = []
    
    updated = False
    
    #iterate the cases to find the one with the step we want step==id
    for case in doc['.cases']:
        if case['id'] == request.POST['id']:
            for attrib in case:
                case[attrib] = request.POST[attrib]
            updated = True
    
    #if we didnt find and update the entry, create a new one
    if not updated:
        c_dict = {}
        for attrib in request.POST:
            c_dict[attrib] = request.POST[attrib]
        doc['.cases'].append(c_dict)
        
    #save the doc changes
    docs[id] = doc
    return HttpResponse(True)

#Get a json structure of all the cases in a project to populate the grid
@login_required    
def get_cases(request):
    id = request.GET['id']
    docs = COUCHDB['testmill']
    doc = docs[id]
    
    try:
        l = len(doc['.cases'])
    except:
        doc['.cases'] = []
        
    c_dict = {}
    c_dict['page'] = "1"
    c_dict['total'] = 1
    c_dict['records'] = str(len(doc['.cases']))
    c_dict['rows'] = []
    c_dict['userdata'] = {}
    
    for case in doc['.cases']:
        r_dict = {}
        r_dict['id'] = case['id']
        r_dict['cell'] = [case['id'], case['assertion'], case['file'], case['bugs'], case['comments'], case['status']]
        c_dict['rows'].append(r_dict)
            
    return HttpResponse(simplejson.dumps(c_dict))

#Ajax get a simple list of the test projects
@login_required
def list(request):
    docs = COUCHDB['testmill']

    func_str = "function(doc) { emit(null, doc);}" 
    results = docs.query(func_str)

    return HttpResponse(simplejson.dumps(results.rows))

#Ajax get a list of recent test project runs from hudson atom feed
@login_required
def feed(request):
    name = request.POST['name']
    
    url = HUDSON+'/view/All/job/'+name+'/rssAll'
    url = url.replace(' ', '%20')
    
    d = feedparser.parse(url)
    
    for e in d.entries:
        e.published_parsed = ''
        e.updated_parsed = ''
    
    return HttpResponse(simplejson.dumps(d.entries))

#Ajax get the base url for hudson UI components
@login_required
def url(request):
    name = request.POST['name']

    url = HUDSON+'/view/All/job/'+name+'/'
    url = url.replace(' ', '%20')
    
    #print "Accessing HUDSON URL", url
    
    return HttpResponse(url)


# @login_required
# def test_rec(request):
#     r_id = request.POST['id']
#     docs = COUCHDB['testmill']
#         
#     return HttpResponse(simplejson.dumps(docs[r_id]))
    

#View page
@login_required
def view(request):
    docs = COUCHDB['testmill']
    
    func_str = "function(doc) { emit(null, doc);}" 
    results = docs.query(func_str)
    
    return render_to_response('projects/view.html',{'rows':results})

#create a new test project page
@login_required
def new(request):
    docs = COUCHDB['testmill']
    if request.method == "POST":
        name = request.POST['name']
        
        #all the preliminary fields to create for the couchdb doc
        a = docs.create({
            'name':name,
            'location':'',
            'tool':'',
            'branch':'',
            'params':'',
            'notes':'',
            'app':'',
            'wiki':'',
            'cli':'',
            '.cases':None,
            'lastBuild':0,
            '.statistic':None
        })
        return HttpResponseRedirect(u"/projects/doc/%s/" % a)
    return render_to_response('projects/new.html',{'rows':docs})

#Ajax get the test file source 
@login_required
def get_file_source(request):
    id = request.POST['id']
    file_path = request.POST['file_path']
    
    docs = COUCHDB['testmill']
    doc = docs[id]
    
    to_host = SOURCE;
    to_project = doc['location'];
    to_file = file_path
    
    url = to_host+to_project.strip()+to_file.strip()
    #print "Accessing URL for file source", url
    url = url.replace(" ", "%20")
    response = urllib2.urlopen(url)
    html = response.read()
    hl = highlight(html, PythonLexer(), HtmlFormatter())
    
    return HttpResponse(hl)

#Render the test project details page
@login_required
def detail(request,id):    
    docs = COUCHDB['testmill']
    try:
        doc = docs[id]
    except ResourceNotFound:
        raise Http404        
    if request.method == "POST":
        # doc['name'] = request.POST['name']
        #  doc['text'] = request.POST['text']
        for e in request.POST:
            doc[e] = request.POST[e]
        docs[id] = doc
    
    # Disable the auto escapeing and do it manually
    # so that input html is rendered
    context_instance=RequestContext(request)
    context_instance.autoescape=False

    return render_to_response('projects/detail.html',{'row':doc, 'id':id, 'ticket':TICKET}, context_instance)

# Update tests statistic
@login_required
def update_test_stat(request):
    docs = COUCHDB['testmill']
    id = request.POST['id']
    isFull = request.POST['full']
    try:
        doc = docs[id]
    except ResourceNotFound:
        raise Http404        
    cases = doc['.cases']
    name = doc['name']
    if (isFull == 'false'):
        try:
            l = len(doc['.statistic'])
        except:
            doc['.statistic'] = []
    else:
        doc['lastBuild'] = 0
        doc['.statistic'] = []
    # Get the number or runs
    #
    url = HUDSON+'view/All/job/'+name+'/api/json'
    url = url.replace(' ', '%20')
    req = urllib2.urlopen(url)
    response = req.read()
    response = simplejson.loads(response)
    lastBuild = int(response['lastCompletedBuild']['number'])
    docLastBuild = int(doc['lastBuild'])
    if(lastBuild > docLastBuild):
        for i in range( docLastBuild, lastBuild + 1):
            # Get child reports link
            url = HUDSON+'view/All/job/'+name+'/'+str(i)+'/testReport/api/json'
            url = url.replace(' ', '%20')
            try:
                req = urllib2.urlopen(url)
                response = req.read()
                response = simplejson.loads(response)
                try:
                    child_url =  str(response['childReports'][0]['child']['url'])
                    child_url = child_url.replace("./", "")
                    # Get test results from this build
                    child_url = child_url + 'testReport/api/json'
                    # Get the list of failed test cases
                    try:
                        req = urllib2.urlopen(child_url)
                        response = req.read()
                        response = simplejson.loads(response)
                        cases_run = response['suites'][0]['cases']
                        results = []
                        for case_run in cases_run:                         
                            for case in cases:
                                fileName = case['file']
                                fileName = fileName.replace(".py", "")                              
                                if (str(case_run['name']) == fileName):
                                    child = {
                                        'name': fileName,
                                        'status': str(case_run['status']),
                                        'error': str(case_run['errorStackTrace'])
                                    }
                                    results.append(child)
                        finalRes = {'buildNumber': i, 'testResults': results} 
                        doc['.statistic'].append(finalRes)                
                        doc['lastBuild'] = i
                        docs[id] = doc
                    except:
                        raise Exception('Stat wasnt added to DB!')
                except: # case when build is failed
                    pass
            except: # case when build doesn't exist
                pass

    return HttpResponse('Stat is updated')
        
# Return test statistic
@login_required
def get_test_stat(request):
    docs = COUCHDB['testmill']
    id = request.GET['id']
    fileName = str(request.GET['file'])
    fileName = fileName.replace('.py', '')
    doc = docs[id]
    c_dict = {}
    c_dict['page'] = "1"
    c_dict['total'] = 1
    c_dict['records'] = str(len(doc['.statistic']))
    c_dict['rows'] = []
    c_dict['userdata'] = {}
    for k in range(len(doc['.statistic'])-1, -1, -1):
    #for build in doc['.statistic']:
    #    for cases in build['testResults']:
        for cases in doc['.statistic'][k]['testResults']:
            if str(cases['name']) == fileName:
     #           bn = str(build['buildNumber'])
                bn = str(doc['.statistic'][k]['buildNumber'])
                r_dict = {}
                r_dict['id'] = cases['status']
                if (cases['status']=='FAILED' or cases['status']=='REGRESSION'):
                    r_dict['cell'] = [bn, cases['status'], '<a href="javascript:showStackTrace(\''+fileName+'\', '+bn+')"> Show details </a>']
                else:
                    r_dict['cell'] = [bn, cases['status'], '&nbsp;']
                c_dict['rows'].append(r_dict)
    return HttpResponse(simplejson.dumps(c_dict))

# Get error stacktrace
@login_required
def get_error_stacktrace(request):
    docs = COUCHDB['testmill']
    id = request.POST['id']
    doc = docs[id]
    fileName = str(request.POST['file'])
    buildNumber = int(request.POST['build'])
    resp = ''
    for build in doc['.statistic']:
        if build['buildNumber'] == buildNumber:
            for case in build['testResults']:
                if case['name'] == fileName:
                    resp = highlight(case['error'], PythonLexer(), HtmlFormatter())
                    #resp = case['error']
    return HttpResponse(resp)