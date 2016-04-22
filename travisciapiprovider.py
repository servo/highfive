import urllib
import json

# If more functionality is needed from this class, it might be a
# better decision to use travispy
class TravisCiApiProvider():
    host_url = 'https://api.travis-ci.org'
    build_url = host_url + '/builds/{build_id}'
    log_url = host_url + '/jobs/{job_id}/log'

    def get_build(self, build_id):
        return json.loads(urllib.urlopen(self.build_url.format(build_id=build_id)).read())


    def _get_job_id(self, build_data, job_index=0):
        try:
            job_id = build_data['matrix'][job_index]['id']
        except IndexError:
            print "job_index out of bounds"
            job_id = -1

        return job_id


    def get_log(self, build_data):
        return urllib.urlopen(self.log_url.format(job_id=self._get_job_id(build_data))).read()


    def get_pull_request_number(self, build_data):
    	return int(build_data['compare_url'].split('/')[-1])
