def check_keyword_exists(keyword_list, subdomain):
    return any(sub in subdomain for sub in keyword_list)
