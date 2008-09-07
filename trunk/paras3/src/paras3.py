#! /usr/bin/env python
# vim: set fileencoding=utf-8

#===============================================================================
# Subversion information:
# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$
#===============================================================================

"""
This is paras3, the parallel s3 sync.
See <http://code.google.com/p/pas3/wiki/paras3> for more information.

The program is released under GPLv3.
"""

# Although this is bad style for a Python program, all the used classes
# and such will be in one single file. Reason: It makes distribution and
# use of the actual program easier for end-users.

import getopt, sys, os

class Paras3:
    # How do I call myself?
    NAME = "paras3"
    
    # Version of the program
    # LCR is replaced by Subversion with the LCR. Because of that, use such a
    # "complicated" alg.
    VERSION = {"major": 0, "minor": 0, "rev": "$LastChangedRevision$".split(" ")[1]}

    # How was the programm called (ie. path)
    ARG0 = sys.argv[0]

    # Which command-line options are supported?
    OPTS = {
        "short": "hsrpDvnPx:c:X:m5",
        "long": ["help", "ssl", "recursive", "public-read", "delete", "verbose",
                 "dryrun", "progress", "expires=", "cache-control=", "exclude=",
                 "make-dirs", "no-md5", "dry-run"]
    }
    
    def __init__(self, args = sys.argv[1:], out=sys.stdout):
        """Initialize the Paras3 class.
        
        @param args: Command line arguments passed by the user to paras3
        @type args: List of strings
        @param out: Where to direct output to
        @type out: File objects corresponding to the interpreter's standard output
        """
        
        # Store command line parameters
        self.args = args
        self.out = out
        
        # How was the programm called (ie. path)
        self.arg0 = sys.argv
        
        # Defaults
        self.ssl = False
        self.recursive = False
        self.public_read = False
        self.delete = False
        self.verbose = False
        self.dryrun = False
        self.progress = False
        self.expires = None
        self.cache_control = None
        self.exclude = None
        self.make_dirs = False
        self.no_md5 = False
        
    def usage(self, ErrorMessage = None):
        """Print usage information for paras3.
        
        @param ErrorMessage: An optional error message which is to be printed.
        @type None or string
        @rtype None
        """
        
        if ErrorMessage is not None: print "Error: %s\n" % (ErrorMessage)
        
        print """%s version %s.%s r%s
Copyright (c) 2008 Alexander Skwar
Web site: http://code.google.com/p/pas3/wiki/paras3

%s is a file transfer program capable of fast, and parallel transfer
to and from Amazon AWS S3 buckets.

Usage: %s [OPTION]... SRC DEST

Options:
 -h, --help:             Print usage information
 -s, --ssl:              Encrypt traffic with SSL
 -r, --recursive:        recurse into directories
 -p, --public-read:      Make files readable by everyone
 -D, --delete:           delete extraneous files from destination dirs
 -v, --verbose:          increase verbosity
 -n, --dryrun:           perform a trial run with no changes made
 -P, --progress:         show progress during transfer
 -x, --expires=DATE:     Make S3 expire files after DATE
 -c, --cache-control=CC: Control how caches ("proxies") should handle traffic
 -X, --exclude=PATTERN:  exclude files matching PATTERN
 -m, --make-dirs:        Create LOCAL dirs, even if there is no s3sync-compatible directory
 -5, --no-md5:           Skip MD5 check
        """ % (
            self.NAME,
            self.VERSION["major"], self.VERSION["minor"], self.VERSION["rev"],
            self.NAME, self.ARG0
        )
        
        return
        
    def parse_command_line_options(self):
        """Interprete the command line options passed along and configure the program.
        
        @rtype: Integer
        @return: 0 if everything was okay, non-0 otherwise
        """
        
        try:
            opts, args = getopt.gnu_getopt(self.args,
                                           self.OPTS["short"], self.OPTS["long"])
        except getopt.GetoptError, err:
            # print help information and exit:
            # "err" will contain something like "option -a not recognized"
            self.usage(str(err))
            return 2
        output = None
        verbose = False
        for o, a in opts:
            if o in ("-h", "--help"):
                self.usage()
                return 0
            elif o in ("-s", "--ssl"):
                self.ssl = True
            elif o in ("-r", "--recursive"):
                self.recursive = True
            elif o in ("-p", "--public-read"):
                self.public_read = True
            elif o in ("-D", "--delete"):
                self.delete = True
            elif o in ("-v", "--verbose"):
                self.verbose = True
            elif o in ("-n", "--dryrun", "--dry-run"):
                self.dryrun = True
            elif o in ("-P", "--progress"):
                self.progress = True
            elif o in ("-x", "--expires"):
                self.expires = a
            elif o in ("-c", "--cache-control"):
                self.cache_control = a
            elif o in ("-X", "--exclude"):
                self.exclude = a
            elif o in ("-m", "--make-dirs"):
                self.make_dirs = True
            elif o in ("-5", "--no-md5"):
                self.no_md5 = True
            else:
                assert False, "unhandled option"
        # ...
        
        return 0
    
    def run(self):
        """Run the program."""
        
        # Parse the command line options that the user gave (or not gave...)
        exit_code = self.parse_command_line_options()
        # Check if all was fine - ie. if PCLO returned 0. Error if != 0.
        if exit_code != 0:
            # Error - bail out.
            return exit_code
        # All well
        

class Config:
    def __init__(self):
        pass

if __name__ == "__main__" or __name__ == sys.argv[0]:
    sys.exit(Paras3(sys.argv[1:], sys.stdout).run())

