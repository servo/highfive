import re

class ErrorLogParser():
	def parse_log(self, log, error_re):
		raise NotImplementedError

class ServoErrorLogParser(ErrorLogParser):
    path_key = 'path'
    position_key = 'position'
    body_key = 'body'

    def parse_log(self, log):
        error_re = "\\x1b\[94m(.+?)\\x1b\[0m:\\x1b\[93m(.+?)\\x1b\[0m:\s\\x1b\[91m(.+?)(?:\\x1b\[0m|$)"
        cont_comment_re = "\t\\x1b\[\d{2}m(.+?)\\x1b\[0m"
        # error_re = "File:\s(.+?)\sLine:\s(.+?)\sComment:\s(.+)"
        # cont_comment_re = "(\t.+)"
        matches = []
        log_list = log.splitlines()

        trimmed_log_list = self._trim_log(log_list, error_re)

        for log_line in trimmed_log_list:
            err_match = re.match(error_re, log_line)
            if err_match:
                matches.append(list(err_match.groups()))
            else:
                cont_comment_match = re.match(cont_comment_re, log_line)
                if cont_comment_match:
                    matches[-1][-1] += "\n{}".format(list(cont_comment_match.groups())[0])

        return self._process_errors(matches)


    def _trim_log(self, log_list, error_re):
        """
        Cut off irrelevant details so cont_comment_re doesn't match something
        that isn't an error comment
        """
        trimmed_log_list = log_list
        err_match = None
        i = 0

        while not err_match and i < len(log_list):
            err_match = re.match(error_re, log_list[i])
            i += 1

        if err_match:
            trimmed_log_list = log_list[i - 1:]

        return trimmed_log_list


    def _process_errors(self, matches):
        return (self._convert_match_to_dict(match) for match in matches)


    def _convert_match_to_dict(self, match):
        return {self.path_key: match[0], self.position_key: int(match[1]), self.body_key: match[2]}
    	