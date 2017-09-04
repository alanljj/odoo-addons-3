# -*- coding: utf-8 -*-
#
# Copyright(C) 2017 Patrik Dufresne Service Logiciel inc. (http://www.patrikdufresne.com).
# PDSL Gitlab plugin
# 
# This file is part of PDSL Gitlab plugin.
# 
# PDSL Gitlab plugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


from collections import namedtuple
from dateutil.parser import parse
import requests
import xmlrpclib
import re


Issue = namedtuple('Issue', ['id', 'project_name', 'title', 'description', 'assignee', 'tags', 'author', 'created_at', 'state', 'milestone', 'web_url', 'notes'])

Note = namedtuple('Note', ['description', 'author', 'created_at'])

Milestone = namedtuple('Milestone', ['name', 'description', 'start_date', 'end_date', 'closed'])

class OdooClient():
    
    def __init__(self, url, db, username, password):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        # Check connection.
        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        common.version()
        # Then authenticate.
        self.uid = common.authenticate(db, username, password, {})
    
    def check_object_exists(self, objname):
        """Check if the given object exists and is accessible for the current user."""
        try:
            models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
            return models.execute_kw(self.db, self.uid, self.password,
                'project.task', 'check_access_rights',
                ['read'], {'raise_exception': False})
        except:
            return False
        
    def create_record(self, objname, data):
        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        rid = models.execute_kw(self.db, self.uid, self.password, objname, 'create', [data])
        return rid
        
    def search_first_record(self, objname, criteria):
        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        data = models.execute_kw(
            self.db, self.uid, self.password,
            objname, 'search_read',
            criteria,
            {'limit': 1})
        if data:
            return data[0]
        
    def search_user(self, identifier):
        r = (self.search_first_record('res.users', criteria=[[['login', '=', identifier]]]) or
            self.search_first_record('res.users', criteria=[[['name', '=', identifier]]]) or 
            self.search_first_record('res.users', criteria=[[['email', '=', identifier]]]))
        return r and r['id']
        
    def create_update_project(self, name):
        r = self.search_first_record('project.project', criteria=[[['name', '=', name]]])
        if not r:
            return self.create_record('project.project', {'name': name})
        return r['id']
    
    def create_update_sprint(self, name, description='', start_date=None, end_date=None, state=None):
        # Check if project.sprint exists.
        if not self.check_object_exists('project.sprint'):
            return None
        
        data = {
            'name': name,
            'description': description,
        }
        if start_date:
            data['datestart'] = start_date.strftime('%Y-%m-%d %H:%M:%S')
        if end_date:
            data['dateend'] = end_date.strftime('%Y-%m-%d %H:%M:%S')
        if state:
            data['state'] = state
        
        # Otherwise create or update the sprint object.
        r = self.search_first_record('project.sprint', criteria=[[['name', '=', name]]])
        if not r:
            return self.create_record('project.sprint', data)
        # Update existing record
        rid = r['id']
        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        models.execute_kw(self.db, self.uid, self.password, 'project.sprint', 'write', [[rid], data])
        return rid
    
    def create_update_project_category(self, name):
        r = self.search_first_record('project.category', criteria=[[['name', '=', name]]])
        if not r:
            return self.create_record('project.category', {'name': name})
        return r['id']
    
    def search_project_task_type(self, name):
        # Trick the search a bit.
        if name == 'closed':
            name = 'Done'
        r = self.search_first_record('project.task.type', criteria=[[['name', '=', name]]])
        return r and r['id']
    
    def create_update_task(self, project_name='', name='', description='', create_date=None, creator='', assignee='', tags=[], stage='', sprint_id=None):
        # Prepare project
        project_id = self.create_update_project(project_name)
        
        # Prepare categories
        categ_ids = [self.create_update_project_category(t) for t in tags]
        
        data = {
            'project_id': project_id,
            'name': name,
            'description': description,
            'categ_ids': [[6, False, categ_ids]],
        }
        if create_date:
            data['create_at'] = create_date.strftime('%Y-%m-%d %H:%M:%S')
        if creator:
            c = self.search_user(creator)
            if c:
                data['create_uid'] = c
        if assignee:
            a = self.search_user(assignee)
            if a:
                data['user_id'] = a
        if stage:
            s = self.search_project_task_type(stage)
            if s:
                data['stage_id'] = s
        if sprint_id:
            data['sprint_id'] = sprint_id
            
        
        # Search existing task
        r = self.search_first_record('project.task', criteria=[[['name', '=', name]]])
        if not r:
            return self.create_record('project.task', data)
        # Update existing record
        rid = r['id']
        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(self.url))
        models.execute_kw(self.db, self.uid, self.password, 'project.task', 'write', [[rid], data])
        return rid

class GitLabClient():
    
    def __init__(self, url, private_token):
        self.url = url;
        self.private_token = private_token;
        
    def _get(self, path, **kwargs):
        return requests.get(self.url + path, headers={'PRIVATE-TOKEN': self.private_token}, **kwargs)
        
    def get_projects(self):
        r = self._get('/api/v4/projects')
        return r.json()

    def get_issues(self, project_id, page=1):
        r = self._get('/api/v4/projects/' + str(project_id) + '/issues', params={'scope':'all', 'per_page': '20', 'page': page})
        return r.json()
    
    def get_issue_notes(self, project_id, issue_id):
        r = self._get('/api/v4/projects/' + str(project_id) + '/issues/' + str(issue_id) + '/notes')
        return r.json()
        
def _md2html(value):
    try:
        import markdown  # @UnresolvedImport
        extensions = ['extra', 'smarty']
        return markdown.markdown(value, extensions=extensions, output_format='html5')
    except:
        return value


def export_gitlab():
    
    client = GitLabClient(
        url='http://git.patrikdufresne.com/',
        private_token='eKNEcSc9KJg9sMuu6vgc'
    )
    
    def _replace_rel_url(project, value):
        """Replace relative url by absolute one."""
        # http://git.patrikdufresne.com/pdsl/minarca/uploads/89467b7f29980e95b128c4c66fe8f4d6/image.png
        return re.sub(r'!\[image\]\(/uploads/', '![image](' + project['web_url'] + '/uploads/', value)    
    
    # Loop on each project, each issue.
    for p in client.get_projects():
        page = 1
        issues = client.get_issues(p['id'], page=page)
        while issues:
            for i in issues:
                # Check if issue has notes:
                notes = [
                    Note(
                        description=_replace_rel_url(p, n['body']),
                        created_at=parse(n['created_at']),
                        author=n['author']['username'],
                    )
                    for n in reversed(client.get_issue_notes(p['id'], i['iid']))
                ]
                if i['milestone']:
                    n = i['milestone']
                    m = Milestone(
                        name=n['title'], 
                        description=n['description'], 
                        start_date=n['start_date'] and parse(n['start_date']), 
                        end_date=n['due_date'] and parse(n['due_date']), 
                        closed=n['state'] != 'active')
                else:
                    m = None
                
                yield Issue(
                    id=i['iid'],
                    project_name=p['name'],
                    title=i['title'],
                    description=_replace_rel_url(p, i['description']),
                    assignee=i['assignee'] and i['assignee']['username'],
                    tags=i['labels'],
                    author=i['author']['username'],
                    created_at=parse(i['created_at']),
                    state=i['state'],
                    milestone=m,
                    web_url=i['web_url'],
                    notes=notes,
                )
            # Get next page
            page += 1
            issues = client.get_issues(p['id'], page=page)

    
def import_odoo(issues, html=True):
    
    def _description_text(i):
        description = i.description
        description += '\n ' + i.web_url
        if i.notes:
            description += '\n\n---'
            for n in i.notes:
                description += '\n'
                description += 'Author: ' + n.author + '\n'
                description += 'Date: ' + str(n.created_at) + '\n'
                description += n.description + '\n'
                description += '---'
        return description
                
    def _description_html(i):
        description = _md2html(i.description)
        description += '<p>Original source: <a href="%s" target="_blank">%s</a></p>' % (i.web_url, i.web_url)
        if i.notes:
            description += '<hr>'
            for n in i.notes:
                description += 'Author: ' + n.author + '<br/>'
                description += 'Date: ' + str(n.created_at) + '<br/>'
                description += _md2html(n.description)
                description += '<hr>'
        return description
    
    # Pick the best description.
    _description = _description_html if html else _description_text
    
    client = OdooClient(
        url='http://althea.patrikdufresne.com:8069',
        db='pdsl-inc',
        username='noreply',
        password='piko0123;',
    )
    
    # Process all the issues
    for i in issues:
        print i.project_name + ' #' + str(i.id)
        
        # Create sprint for milestone
        if i.milestone:
            sprint_id = client.create_update_sprint(
                name=i.milestone.name,
                description=i.milestone.description,
                start_date=i.milestone.start_date,
                end_date=i.milestone.end_date,
                state='done' if i.milestone.closed else None)
        else:
            sprint_id = None
        
        rid = client.create_update_task(
            project_name=i.project_name,
            name=i.title,
            description=_description(i),
            create_date=i.created_at,
            creator=i.author,
            tags=i.tags,
            assignee=i.assignee,
            stage=i.state,
            sprint_id=sprint_id
        )

def main():
    """called with source destination"""
    issues = export_gitlab()
    import_odoo(issues)
    
if __name__ == '__main__':
    main()
