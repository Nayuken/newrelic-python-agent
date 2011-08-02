'''
Created on Jul 26, 2011

@author: sdaubin
'''
import json,httplib,os,socket,string,time
from newrelic.core.exceptions import raise_newrelic_exception,ForceRestartException,ForceShutdownException
from newrelic.core.config import create_configuration
from newrelic.core import environment

class NewRelicService(object):
    def __init__(self, remote,app_names=["FIXME Python test"]):
        self._remote = remote
        self._agent_run_id = None
        self._app_names = app_names
        self._configuration = None
        self._metric_data_time = time.time()

    def get_configuration(self):
        return self._configuration

    def get_agent_run_id(self):
        return self._agent_run_id

        
    def agent_version(self):
        #FIXME move this
        return "0.9.0"
        
    def shutdown(self):
        if self.agent_run_id is not None:
            try:
                conn = self._remote.create_connection()
                try:
                    self.invoke_remote(conn, "shutdown", True, self._agent_run_id)
                finally:
                    conn.close()

            except Exception as ex:
                #FIXME log
                print ex
                pass
            self._agent_run_id = None
        
    def connected(self):
        return self._agent_run_id is not None    
        
    def connect(self,conn=None):
        create_conn = conn is None
        if create_conn:
            conn = self._remote.create_connection()
        try:
            redirect_host = self.invoke_remote(conn, "get_redirect_host", True, None)
            
            if redirect_host is not None:
                self._remote.host = redirect_host
                print "Collector redirection to %s" % redirect_host
    
            self.parse_connect_response(self.invoke_remote(conn, "connect", True, None, self.get_start_options()))
        finally:
            if create_conn:
                conn.close()
            
        return self.connected()
    
    def send_error_data(self,conn,error_data):
        if not self.connected():
            raise "Not connected"
        res = self.invoke_remote(conn,"error_data",True,self._agent_run_id,self._agent_run_id,error_data)
        return res         
    
    def send_metric_data(self,conn,metric_data):
        if not self.connected():
            raise "Not connected"
        now = time.time()
        res = self.invoke_remote(conn,"metric_data",True,self._agent_run_id,self._agent_run_id,self._metric_data_time,now,metric_data)
        self._metric_data_time = now
        return res         
            
    def get_app_names(self):
        return self._app_names
        
    def get_identifier(self):
        return string.join(self.get_app_names(),',')
        
    def get_start_options(self):
        options = {"pid":os.getpid(),"language":"python","host":socket.gethostname(),"app_name":self.get_app_names(),"identifier":self.get_identifier(),"agent_version":self.agent_version(),"environment":environment.environment_settings()}
        '''
        # FIXME 
            if (agent.Config.BootstrapConfig.ServiceConfig.SendEnvironmentInfo) {
                map.Add("environment", agent.Environment);
                map.Add("settings", agent.Config);
            }
        '''

        return options
    
    def parse_connect_response(self, response):
        if "agent_run_id" in response:
            self._agent_run_id = response.pop("agent_run_id")
        else:
            raise Exception("The connect response did not include an agent run id: %s", str(response))
        
        # we're hardcoded to a 1 minute harvest
        response.pop("data_report_period")
        
        self._configuration = create_configuration(response)
        
    def invoke_remote(self, connection, method, compress = True, agent_run_id = None, *args):
        try:
            return self._remote.invoke_remote(connection, method, compress, agent_run_id, *args)
        except ForceShutdownException as ex:
            self._agent_run_id = None
            raise ex
        except ForceRestartException as ex:
            self._agent_run_id = None
            raise ex            
    
    agent_run_id = property(get_agent_run_id, None, None, "The agent run id")
    configuration = property(get_configuration, None, None, None)
    
class NRJSONEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        return json.JSONEncoder.default(self, o)
    
'''
    def iterencode(self, obj, _one_shot=False):
        if hasattr(obj, '_asdict'):
            gen = json.JSONEncoder.iterencode(self, obj._asdict(), _one_shot=False)
        else:
            gen = json.JSONEncoder.iterencode(self, obj, _one_shot)
        for chunk in gen:
            yield chunk
'''

class JSONRemote(object):
    '''
    classdocs
    '''

    PROTOCOL_VERSION = 9

    def __init__(self, license_key, host, port):
        '''
        Constructor
        '''
        self._host = host
        self._port = port
        self._protocol = "http://"
        self._license_key = license_key
        self._encoder = NRJSONEncoder()

    def get_host(self):
        return self._host


    def set_host(self, value):
        self._host = value

        
    def create_connection(self):
        # FIXME add ssl support
        conn = httplib.HTTPConnection(self._host, self._port)        
        conn.connect()
        return conn
    
    def raise_exception(self, ex):
        # REVIEW 
        if "error_type" in ex and "message" in ex:
            raise_newrelic_exception(ex["error_type"], ex["message"])            
            
        raise Exception("Unknown exception: %s" % str(ex))
    
    def parse_response(self, str):
        try:
            res = json.loads(str)
        except Exception as ex:
            # FIXME log json
            raise Exception("Json load failed error:", ex.message, ex)
        
        if "exception" in res:
            self.raise_exception(res["exception"])            
        if "return_value" in res:
            return res["return_value"]
        
        raise Exception("Unexpected response format: %s" % str)
        
        
    def invoke_remote(self, connection, method, compress = True, agent_run_id = None, *args):
        json_data = self._encoder.encode(args)
        url = self.remote_method_uri(method, agent_run_id)
        
        headers = {"Content-Encoding" : "identity" } # FIXME deflate
        connection.request("POST", url, json_data, headers)
        response = connection.getresponse()
        
        encoding = response.getheader("Content-Encoding")
        
        if response.status is httplib.OK:
            reply = response.read()
            try:
                return self.parse_response(reply)
            except Exception as ex:
                print json_data
                raise ex
        else:
            raise Exception("%s failed: status code %i" % (method, response.status))
        
    
    def remote_method_uri(self, method, agent_run_id = None):
        uri = "/agent_listener/%i/%s/%s?marshal_format=json" % (self.PROTOCOL_VERSION,self._license_key,method)
        if agent_run_id is not None:
            uri += "&run_id=%i" % agent_run_id
        return uri
    
    host = property(get_host, set_host, None, "The New Relic service host")
        
    