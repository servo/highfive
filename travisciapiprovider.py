import urllib
import json

# If more functionality is needed from this class, it might be a
# better decision to use travispy
class TravisCiApiProvider():
    host_url = 'https://api.travis-ci.org'
    build_url = host_url + '/builds/{build_id}'
    log_url = host_url + '/jobs/{job_id}/log'

    def get_build(self, build_id):
        url = self.build_url.format(build_id=build_id)
        return json.loads(urllib.urlopen(url).read())

    def get_pull_request_number(self, build_data):
    	return int(build_data['compare_url'].split('/')[-1])
