# library to read and parse osm and osh files
import osmium as osm

# for sorting our results
from operator import itemgetter

# command line option parser
import argparse
import json

# check if input file exists
import os.path

# error message
import sys

# file timestamp
import time

# multiplier to calc a score
way_multi = 5
rel_multi = 10

min_score = 50

output_file = 'index.html'

# Input handler for full history data
class OSMHistoryHandler(osm.SimpleHandler):
    def __init__(self):
        osm.SimpleHandler.__init__(self)
        self.processed_o = set([]) # OSM IDs of objects we already have processed
        self.processed_u = set([]) # OSM user names of users we already have in result list
                                   # check against a set is multiple times faster than using a list or dict

        self.processed_u_pos = {}  # position for each user in user_list of already processed users
                                   # faster than check position every time by list iteration

        self.user_list = []        # result list with user name, node count, ways count, relation count

        self.t_nodes = 0           # count number of processed nodes, ways, relations
        self.t_ways = 0
        self.t_relations = 0

    # callback for nodes, ways and relations
    # count the total per object type and call the function to count given tag per user
    def node(self, n):
        self.count_tags(n, 'node')
        self.t_nodes = self.t_nodes +1

    def way(self, n):
        self.count_tags(n, 'way')
        self.t_ways = self.t_ways +1

    def relation(self, n):
        self.count_tags(n, 'relation')
        self.t_relations = self.t_relations +1

    # count the tags created per user
    def count_tags(self,osm_object, osm_type):

        # position of a user in the result list of lists
        def user_in_list(user,user_list):
            found = 0
            for num, sublist in enumerate(user_list, start=0):
                if sublist[0] == user:
                    found = num
                    break
            return(found)

        # if osm ID is not in our list of already processed objects
        # Same OSM IDs can mean a node, way or relation, so store n,w or r after the number for identification
            # and the osm tag is what we are looking for or empty = *
        if ((osm_type[0]+str(osm_object.id)) not in self.processed_o) :
            if (osm_tag in osm_object.tags) or (osm_tag == '*'):
                # if the user is unknown, create an entry in the result list, add username to the set of processed users, 
                # and save the position of the user in the list in a dict 
                if (osm_object.user not in self.processed_u):
                    # Result list to store name, number of nodes, ways, relations
                    self.user_list.append([osm_object.user,0,0,0])
                    # user name set (much faster that dict or list)
                    self.processed_u.add(osm_object.user)
                    # dict with user name and position of the user in the result list
                    self.processed_u_pos.update({osm_object.user : user_in_list(osm_object.user, self.user_list)})

                # get the position of the user in the result list of the current object
                user_pos = self.processed_u_pos[osm_object.user]

                # add +1 to the result list depending on object type
                if osm_type == 'node':
                    self.user_list[user_pos][1] =  self.user_list[user_pos ][1] + 1
                elif osm_type == 'way':
                    self.user_list[user_pos][2] =  self.user_list[user_pos ][2] + 1
                elif osm_type == 'relation':
                    self.user_list[user_pos][3] =  self.user_list[user_pos ][3] + 1

                # add the OSM ID + n,w or r to the set of already processed objects
                self.processed_o.add(osm_type[0]+str(osm_object.id))

# if we find an error, print message and wave good bye
def report_error(message):
    sys.stderr.write("{}\n".format(message))
    exit(1)

# design & javascript
# https://datatables.net
# header and column labels in_file and tag for introduction text, titles for column titles
def html_header(html_file, tag, in_file,titles):
    with open(html_file, 'w') as preview_html:
        print('<!DOCTYPE html>', file=preview_html)
        print('<html lang="en">', file=preview_html)
        print('<meta charset="utf-8"/>', file=preview_html)
        print('<head>', file=preview_html)
        print(' <title>OSM User/Tag statistic</title>', file=preview_html)
        print(' <link rel="stylesheet" type="text/css" href="https://www.codegeo.de/stats/jquery.dataTables.min.css">', file=preview_html)
        print(' <style type="text/css" class="init">', file=preview_html)
        print(' </style>', file=preview_html)

        print('<style>', file=preview_html)
        print('      h1 { font-size: 2.0em; }', file=preview_html)
        print('      p  { font-size: 0.8em; }', file=preview_html)
        print('   </style>', file=preview_html)

        print(' <script type="text/javascript" language="javascript" src="https://www.codegeo.de/stats/jquery-3.3.1.js"></script>', file=preview_html)
        print(' <script type="text/javascript" language="javascript" src="https://www.codegeo.de/stats/jquery.dataTables.min.js"></script>', file=preview_html)


        print('    <script type="text/javascript" class="init">', file=preview_html)
        print('       $(document).ready(function() {', file=preview_html)
        print(r'''         var t = $('#example').DataTable( {''', file=preview_html)
        print('               "lengthMenu": [ 25, 50, 100 ],"pageLength": 50,', file=preview_html)
        print('               "columnDefs": [ {', file=preview_html)
        print('                   "searchable": false,', file=preview_html)
        print('                   "orderable": false,', file=preview_html)
        print('                   "targets": 0', file=preview_html)
        print('               } ],', file=preview_html)
        print(r'''            "order": [[ 5, 'desc' ]]''', file=preview_html)
        print('            } );', file=preview_html)
 
        print('       } );', file=preview_html)

        print('    </script>', file=preview_html)
        print(' </head>', file=preview_html)
        print(' <body class="wide comments example">', file=preview_html)
        print('     <div class="content">', file=preview_html)
        print('       <h1 class="page_title">OSM User Statistic</h1>', file=preview_html)
        print('	<div class="info">', file=preview_html)
        print('	    <p> Full history OSM data  - user added the tag ',tag,' to x objects</p>', file=preview_html)
        print('     <p> File parsed :',in_file, '</p>',file=preview_html)
        print('     <p> File timestamp : %s' % time.ctime(os.path.getmtime(in_file)),'</p>', file=preview_html)
        print('     <p> Score = node*1 + ways*', way_multi, ' + relations*',rel_multi,' </p>', file=preview_html)
        print('	    <p>  <br>  </p>', file=preview_html)
        print(' </div>', file=preview_html)
        print(' <table id="example" class="display" style="width:100%">', file=preview_html)
        print('    <thead>', file=preview_html)
        print('        <tr>', file=preview_html)
        for column_name in titles:
            print('            <th>',column_name,'</th>', file=preview_html)
        print('        </tr>', file=preview_html)
        print('    </thead>', file=preview_html)
        print('    <tbody>', file=preview_html)



def html_footer(html_file):
    with open(html_file, 'a') as preview_html:
        print('    </tbody>', file=preview_html)
        print('</table>', file=preview_html)

def html_line(html_file, data_line):
    with open(html_file, 'a') as preview_html:
        print('            <tr>', file=preview_html)
        for data_item in data_line:
            print('                <td>', end='', file=preview_html)
            print(data_item,    end='', file=preview_html)
            print('                </td>', file=preview_html)
        print('            </tr>', file=preview_html)



# main program
if __name__ == '__main__':


    # parsing command line arguments
    parser = argparse.ArgumentParser(description="Parse a OSM history file and provide a node/way/relation per user for specific tag")
    parser.add_argument("-f", "--file", default=None,         help="Input OSM history file", type=str)
    parser.add_argument("-t", "--tag",  default=None,         help="OSM tag to filter", type=str)
    parser.add_argument("-o", "--out",  default="index.html", help="output html file for results", type=str)
    parser.add_argument("-m", "--min",  default=100,          help="minimum OSM score for including in result", type=int)


    args = parser.parse_args()
    settings = {}

    # assign arguments and make some sanity checks
    osh_file = settings.get("file", args.file)
    if (osh_file == None):
        report_error("Please provide Input file with -f or --file")

    if (not (os.path.isfile(osh_file) )):
        report_error("Input file (osh) does not exist")

    osm_tag     = settings.get("tag", args.tag)
    if (osm_tag == None):
        report_error("No tag for filtering provided with -t or --tag")

    min_score   = settings.get("min", args.min)
    output_file = settings.get("out", args.out)



    # create osmium object and apply input file to it
    osh_handler = OSMHistoryHandler()
    osh_handler.apply_file(osh_file, locations=True, idx='sparse_mem_array')

    # get the result list and calc a scoring and total count
    result = []
    for line in osh_handler.user_list:
        line.append(line[1] + line[2]*way_multi + line[3]*rel_multi)
        line.append(line[1] + line[2] + line[3])

    # sort result list of list
    sorted_result = sorted(osh_handler.user_list, key=itemgetter(4), reverse=True)
    
    # add ranking to list with final results
    for rank, line in enumerate(sorted_result, start =1):
        result.append ([rank,line[0], line [1], line [2], line[3], line[4], line[5]]) 


    # print top 25 to command line
    for pos,line in enumerate(result, start = 1):
        print(line)
        if (pos > 24):
            break
    # define column titles for the html tables and generate the first part of the html file
    titles = ['Rank','User','Nodes','Ways','Relations','Score', 'Count']
    html_header(output_file, osm_tag,osh_file, titles)


    # add line by line to the html file as long as the result is over min score
    for line in result:
        if (line[5]<min_score):
            break
        html_line(output_file,line)

    # close the table in html and write the file
    html_footer(output_file)


    # just some numbers to command line
    print('##########################')
    print('Total node-versions processed     : {:,}'.format(osh_handler.t_nodes))
    print('Total way-versions processed      : {:,}'.format(osh_handler.t_ways))
    print('Total relation-versions processed : {:,}'.format(osh_handler.t_relations))


