from JumpScale import j
import yaml
import os
import requests

# this is not everything these are only the base components and can be added to


class Portal(object):
    """
    Class used to define the portal service
    """
    def __init__(self, path='/opt/cfg/system/system-config.yaml'):
        with open(path) as file_discriptor:
            data = yaml.load(file_discriptor)
        self.config = data
        self.__authheaders = None
        if not self.config['itsyouonline'].get('clientId'):
            raise RuntimeError('clientId is not set')
        if not self.config['itsyouonline'].get('clientSecret'):
            raise RuntimeError('clientSecret is not set')

        self.client_id = self.config['itsyouonline']['clientId']
        self.client_secret = self.config['itsyouonline']['clientSecret']
        # baseurl = "https://staging.itsyou.online/"
        self.baseurl = "https://itsyou.online/"

    @property
    def authheaders(self):
        if self.__authheaders is None:
            accesstokenparams = {'grant_type': 'client_credentials',
                                 'client_id': self.client_id, 'client_secret': self.client_secret}
            accesstoken = requests.post(os.path.join(self.baseurl, 'v1', 'oauth',
                                                     'access_token'), params=accesstokenparams)
            token = accesstoken.json()['access_token']
            self.__authheaders = {'Authorization': 'token %s' % token}
        return self.__authheaders

    def configure_api_key(self, apikey):
        label = apikey['label']
        result = requests.get(os.path.join(self.baseurl, 'api', 'organizations', self.client_id,
                                           'apikeys', label), headers=self.authheaders)
        if result.status_code == 200:
            stored_apikey = result.json()
            if apikey['callbackURL'] != stored_apikey['callbackURL']:
                print('API key does not match callback url deleting it')
                requests.delete(os.path.join(self.baseurl, 'api', 'organizations', self.client_id,
                                             'apikeys', label), headers=self.authheaders)
                apikey = {}
            else:
                apikey = stored_apikey

        if 'secret' not in apikey:
            print('Creating API key')
            result = requests.post(os.path.join(self.baseurl, 'api', 'organizations',
                                                self.client_id, 'apikeys'), json=apikey, headers=self.authheaders)
            apikey = result.json()
        return apikey

    def add_user(self):
        """
        Add portal user using jsuser.
        """
        user = self.config['environment'].get('user', 'admin')
        passwd =  self.config['environment']['password']
        cmd1 = 'jsuser list'
        res = j.do.execute(cmd1, dieOnNonZeroExitCode=False)[1]
        for line in res.splitlines():
            if line.find(user) != -1:
                return

        cmd2 = 'jsuser add -d %s:%s:admin:fakeemail.test.com:jumpscale' % (user, passwd)
        j.do.execute(cmd2, dieOnNonZeroExitCode=False)


    def configure_user_groups(self, service):
        ovc_environment = self.config['itsyouonline']['environment']
        gid = j.application.whoAmI.gid
        fqdn = '%s.%s' % (self.config['environment']['subdomain'], self.config['environment']['basedomain'])
        portal_links = {
            'ays': {
                'name': 'At Your Service',
                'url': '/AYS',
                'scope': 'admin',
                'theme': 'light',
            },
            'vdc': {
                'name': 'End User',
                'url': fqdn,
                'scope': 'user',
                'theme': 'dark',
                'external': 'true'},
            'ovs': {
                'name': 'Storage',
                'url': 'ovs-%s' % (fqdn),
                'scope': 'ovs_admin',
                'theme': 'light',
                'external': 'true'},
            'grafana': {
                'name': 'Statistics',
                'url': '/grafana',
                'scope': 'admin',
                'theme': 'light',
                'external': 'true'},
            'grid': {
                'name': 'Grid',
                'url': '/grid',
                'scope': 'admin',
                'theme': 'light'},
            'system': {
                'name': 'System',
                'url': '/system',
                'scope': 'admin',
                'theme': 'light'},
            'cbgrid': {
                'name': 'Cloud Broker',
                'url': '/cbgrid',
                'scope': 'admin',
                'theme': 'light'},
        }
        for linkid, data in portal_links.iteritems():
            if data['url']:
                service.hrd.set('instance.navigationlinks.%s' % linkid, data)
        service.hrd.set('instance.param.cfg.defaultspace', 'vdc')
        service.hrd.set('instance.param.cfg.force_oauth_instance', 'itsyouonline')
        service.hrd.save()
        scl = j.clients.osis.getNamespace('system')
        ccl = j.clients.osis.getNamespace('cloudbroker')

        # setup user/groups
        for groupname in ('user', 'ovs_admin', 'level1', 'level2', 'level3'):
            if not scl.group.search({'id': groupname})[0]:
                group = scl.group.new()
                group.gid = gid
                group.id = groupname
                group.users = ['admin']
                scl.group.set(group)

        # set location
        if not ccl.location.search({'gid': j.application.whoAmI.gid})[0]:
            loc = ccl.location.new()
            loc.gid = j.application.whoAmI.gid
            loc.name = ovc_environment
            loc.flag = 'black'
            loc.locationCode = ovc_environment
            ccl.location.set(loc)
        # set grid
        if not scl.grid.exists(j.application.whoAmI.gid):
            grid = scl.grid.new()
            grid.id = j.application.whoAmI.gid
            grid.name = ovc_environment
            scl.grid.set(grid)

        service.stop()

    def configure_IYO(self):
        if not self.config['itsyouonline'].get('callbackURL'):
            raise RuntimeError('callbackURL is not set')
        if not self.config['itsyouonline'].get('environment'):
            raise RuntimeError('environment is not set')
        callbackURL = self.config['itsyouonline']['callbackURL']
        environment = self.config['itsyouonline']['environment']
        groups = ['admin', 'level1', 'level2', 'level3', 'ovs_admin', 'user']

        # register api key
        apikeyname = 'openvcloud-{}'.format(environment)
        apikey = {'callbackURL': callbackURL,
                  'clientCredentialsGrantType': False,
                  'label': apikeyname
                  }
        apikey = self.configure_api_key(apikey)

        # install oauth_client
        scopes = ['user:name', 'user:email']
        for group in groups:
            scopes.append('user:memberof:{}.{}'.format(self.client_id, group))

        data = {'instance.oauth.client.id': self.client_id,
                'instance.oauth.client.logout_url': '',
                'instance.oauth.client.redirect_url': callbackURL,
                'instance.oauth.client.scope': ','.join(scopes),
                'instance.oauth.client.secret': apikey['secret'],
                'instance.oauth.client.url': os.path.join(self.baseurl, 'v1/oauth/authorize'),
                'instance.oauth.client.url2': os.path.join(self.baseurl, 'v1/oauth/access_token'),
                'instance.oauth.client.user_info_url': os.path.join(self.baseurl, 'api/users/{username}/info')
                }
        oauthclient = j.atyourservice.get(domain='jumpscale', name='oauth_client', instance='itsyouonline')
        for key, val in data.items():
            oauthclient.hrd.set(key, val)
        oauthclient.hrd.save()

        # configure groups on itsyouonline
        for group in groups:
            suborgname = self.client_id + '.' + group
            suborg = {'globalid': suborgname}
            print('Check if group %s exists' % suborgname)
            result = requests.get(os.path.join(self.baseurl, 'api', 'organizations', suborgname),
                                  headers=self.authheaders)
            if result.status_code != 200:
                print('Creating group {}'.format(suborgname))
                result = requests.post(os.path.join(self.baseurl, 'api', 'organizations',
                                                    self.client_id), json=suborg, headers=self.authheaders)
                if result.status_code >= 400:
                    raise RuntimeError("Failed to create suborg {}. Error: {} {}".format(
                        suborgname, result.status_code, result.text))

        # configure portal to use this oauthprovider and restart
        fqdn = '%s.%s' % (self.config['environment']['subdomain'], self.config['environment']['basedomain'])
        portal = j.atyourservice.get(name='portal', instance='main')
        portal.hrd.set('instance.param.cfg.force_oauth_instance', 'itsyouonline')
        portal.hrd.set('instance.param.dcpm.url', fqdn)
        portal.hrd.set('instance.param.ovs.url', 'ovs-%s' % (fqdn))
        portal.hrd.set('instance.param.portal.url', fqdn)

        portal.hrd.save()
        j.do.execute('ln -s /opt/jumpscale7/')
        return portal

    def patch_mail_client(self):
        mailclient = j.atyourservice.get(domain='jumpscale', name='mailclient', instance='main')
        for key, value in self.config['mailclient'].items():
            mailclient.hrd.set('instance.smtp.%s' % key, value)
        mailclient.hrd.save()

if __name__ == '__main__':
    portal = Portal()
    portal.add_user()
    service = portal.configure_IYO()
    portal.configure_user_groups(service)
    portal.patch_mail_client()
