#!/usr/bin/env python
import os, sys
import ROOT
import argparse
import subprocess
import random
ROOT.PyConfig.IgnoreCommandLineOptions = True
from importlib import import_module
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.NanoAODTools.postprocessing.wmass.SequenceBuilder import SequenceBuilder

# example
# python postproc.py -o /eos/cms/store/cmst3/group/wmass/w-mass-13TeV/postNANO/dec2020/DYJetsToMuMu_postVFP/ -d /eos/cms/store/cmst3/group/wmass/sroychow/nanov8/DYJetsToMuMu_M-50_TuneCP5_13TeV-powhegMiNNLO-pythia8-photos/RunIISummer20UL16MiniAOD-106X_mcRun2_asymptotic_v13-v2/  --passall 1 --eraVFP postVFP --isMC 1
# condor options
# -condor --condorDir postprocDY_postVFP -t 86400 -j ZmumuPostVFP -n 2

# for skims (check skimmer.py)
# --doSkim 2 --runOnlySkim --noPostfixSkim (check meaning of these options below)

def makeDummyFile():
    f = open('dummy_exec.sh', 'w')
    f.write('''#!/bin/bash
echo '===setting outdir'
OUTDIR=$1
echo '===changing into proper directory'
cd {pwd}
echo '===doing cmsenv'
eval $(scramv1 runtime -sh);
echo '===moving back to the node'
cd -
echo '===copying keppdropfiles'
cp {pwd}/keep_and_drop*.txt .
shift
echo '===this is pwd at the moment'
pwd
echo '===now running command'
echo python $@ -o $PWD
python $@ -o $PWD
echo '====doing ls in current dir'
ls
echo '===now compressing the files into subdir'
mkdir compressed
for i in `ls *.root`; 
do
    hadd -ff compressed/$i $i;
done
echo '===now copying the files to eos!'
eos cp compressed/*.root $OUTDIR/
echo '===done'
'''.format(pwd=os.environ['PWD']))
    f.close()

def getLinesFromFile(fname):
    try:
        with open(fname, 'r') as f:
            return f.readlines()
    except IOError as e:
        print("In getLinesFromFile(): couldn't open or read from file %s (%s)." % (fname,e))
    
    

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

parser = argparse.ArgumentParser("")
parser.add_argument('-jobNum',    '--jobNum',   type=int, default=1,      help="")
parser.add_argument('-crab',      '--crab',     type=int, default=0,      help="")
parser.add_argument('-passall',   '--passall',  type=int, default=0,      help="")
parser.add_argument('-isMC',      '--isMC',     type=int, default=1,      help="")
parser.add_argument('-maxEvents', '--maxEvents',type=int, default=-1,	  help="")
parser.add_argument('-dataYear',  '--dataYear', type=int, default=2016,   help="")
parser.add_argument('-jesUncert', '--jesUncert',type=str, default="Total",help="")
parser.add_argument('-redojec',   '--redojec',  type=int, default=0,      help="")
parser.add_argument('-runPeriod', '--runPeriod',type=str, default="",    help="")
parser.add_argument('-genOnly',   '--genOnly',  type=int, default=0,      help="")
parser.add_argument('-trigOnly',  '--trigOnly', type=int, default=0,      help="")
parser.add_argument('-iFile',     '--iFile',    type=str, default="",     help="")
parser.add_argument('-c',         '--compression', type=str , default="LZMA:9" , help="Compression algorithm")
parser.add_argument(              '--runNoModules',   action='store_true',      help="Do not run any module, it will just reproduce the input (possibly removing branches or changing compression with --compression, for example)")
parser.add_argument('-doSkim',    '--doSkim',   type=int, choices=[0, 1, 2], default=0,      help="If > 0, run modules for skimming (1=skim for 1 lep space, 2=skim for 2 lep space")
parser.add_argument('-runOnlySkim',    '--runOnlySkim', action='store_true', help="If using doSkim>0, only the skimming module will be run (useful on postprocessed NanoAOD)")
parser.add_argument('-noPostfixSkim',    '--noPostfixSkim', action='store_true', help="Do not add '_Skim' as postfix to the output name (e.g., when using doSkim >0, as it is already present)")
parser.add_argument(              '--isTest',   action='store_true',      help="run test modules, hardcoded inside SequenceBuilder.py (will use keep_and_drop_TEST.txt)")
parser.add_argument('--customKeepDrop',         type=str, default="",     help="use this file for keep-drop")
parser.add_argument('-o',         '--outDir',   type=str, default=".",    help="output directory")
parser.add_argument('-eraVFP',    '--eraVFP',   type=str, default="",     help="Specify one key in ['preVFP','postVFP'] to run on UL2016 MC samples. Only works with --isMC and --dataYear 2016")
parser.add_argument('-condor'   , '--condor',  action='store_true',     help="run on condor instead of locally or on crab")
parser.add_argument('-d'         , '--dsdir'    , type=str , default="", help="input directory of dataset, to be given with condor option!")
parser.add_argument('-n'         , '--nfiles'   , type=int , default=5 , help="number of files to run per condor job")
parser.add_argument('-j'         , '--jobname'  , type=str , default="" , help="Assign name to condor job, for easier tracking (by default the cluster ID is by condor_q)")
parser.add_argument('-t'         , '--runtime'  , type=int , default=43200 , help="MaxRunTime for condor jobs, in seconds")
parser.add_argument('-condorDir' , '--condorDir', type=str , default="", help="Mandatory to run with condor, specify output folder to save condor files, logs, etc...")
parser.add_argument('-condorSkipFiles' , '--condorSkipFiles', type=str , default="", help="When using condor, can specify a file containing a list of files to be skipped (useful for resubmitting failed jobs)")
parser.add_argument('-condorSelectFiles' , '--condorSelectFiles', type=str , default="", help="As --condorSkipFiles, but keep only these ones (useful for resubmitting failed jobs)")
parser.add_argument("-xc", '--executeCondor',   action='store_true',      help="When using condor, submit the command (by default the submit file is only printed on stdout)")


args = parser.parse_args()
isMC      = args.isMC
crab      = args.crab
passall   = args.passall
dataYear  = args.dataYear
maxEvents = args.maxEvents
runPeriod = args.runPeriod
redojec   = args.redojec
jesUncert = args.jesUncert
genOnly   = args.genOnly
trigOnly  = args.trigOnly
inputFile = args.iFile
isTest    = args.isTest
customKeepDrop = args.customKeepDrop
outDir = args.outDir 
eraVFP = args.eraVFP

isData = not isMC

if args.runOnlySkim and not args.doSkim:
    print "--runOnlySkim requires --doSkim {1,2}"
    exit(1)

if outDir not in [".", "./"]:
    print "Creating output directory"
    cmd = "mkdir -p {d}".format(d=outDir)
    print cmd
    os.system(cmd)

print "isMC =", bcolors.OKBLUE, isMC, bcolors.ENDC, \
    "genOnly =", bcolors.OKBLUE, genOnly, bcolors.ENDC, \
    "crab =", bcolors.OKBLUE, crab, bcolors.ENDC, \
    "condor =", bcolors.OKBLUE, args.condor, bcolors.ENDC, \
    "passall =", bcolors.OKBLUE, passall,  bcolors.ENDC, \
    "dataYear =",  bcolors.OKBLUE,  dataYear,  bcolors.ENDC, \
    "maxEvents =", bcolors.OKBLUE, maxEvents, bcolors.ENDC 

if genOnly and not isMC:
    print "Cannot run with --genOnly=1 option and data simultaneously"
    exit(1)
if trigOnly and not isMC:
    print "Cannot run with --trigOnly=1 option and data simultaneously"
    exit(1)
if isMC and dataYear == 2016:
    if eraVFP not in ['preVFP', 'postVFP']:
        print "Have to specify VFP era when running on 2016 MC using --eraVFP (preVFP|postVFP)"
        exit(1)
if isData and not runPeriod:
    # run period (B,C,D,...) could be guessed from input directory, at least when using condor
    # for now let's force the user to specify the correct one
    print "Need to specify a run period when running data"
    exit(1)

if args.condor:
    if not args.condorDir:
        print "Have to specify output folder for logs and files when using condor, with --condorDir <name>"
        exit(1)
    if crab:
        print "Options --crab and --condor are not compatible"
        exit(1)
    if not args.dsdir:
        print 'if you run on condor, give a path which contains the dataset with --dsdir <path>'
        exit(1)
    if args.condorSkipFiles and args.condorSelectFiles:
        print 'options --condorSkipFiles and --condorSelectFiles are not compatible, only one list makes sense'
        exit(1)
        



# run with crab
if crab:
    from PhysicsTools.NanoAODTools.postprocessing.framework.crabhelper import inputFiles,runsAndLumis

    #print bcolors.OKBLUE, "No module %s will be run" % "muonScaleRes", bcolors.ENDC
################################################ GEN
Wtypes = ['bare', 'preFSR', 'dress'] ## this isn't used... good, because bare and dress no longer exists

##This is temporary for testing purpose
#input_dir = "/gpfs/ddn/srm/cms/store/"
input_dir = "root://cms-xrd-global.cern.ch//eos/cms/store/"

ifileMC = ""
if dataYear==2016:
    ifileMC="/cmst3/group/wmass/w-mass-13TeV/NanoAOD/DYJetsToMuMu_M-50_TuneCP5_13TeV-powhegMiNNLO-pythia8-photos/NanoAODv7/201025_173845/0000/SMP-RunIISummer16NanoAODv7-00336_1.root"
elif dataYear==2017:
    ifileMC = "mc/RunIIFall17NanoAODv5/WJetsToLNu_Pt-50To100_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/PU2017_12Apr2018_Nano1June2019_102X_mc2017_realistic_v7-v1/20000/B1929C77-857F-CA47-B352-DE52C3D6F795.root"
elif dataYear==2018:
    ifileMC = "mc/RunIIAutumn18NanoAODv5/WJetsToLNu_Pt-50To100_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/Nano1June2019_102X_upgrade2018_realistic_v19-v1/100000/FEF8F001-02FD-E449-B1FC-67C8653CDCEC.root"

ifileDATA = ""
if not isMC: 
    #input_dir = 'root://xrootd.ba.infn.it//store/'
    if dataYear==2016:
        #ifileDATA = "/eos/cms/store/data/Run2016H/SingleMuon/NANOAOD/Nano02Dec2019-v1/270000/062790E9-2D36-FF42-9525-BCD698324ED0.root"
        ifileDATA = "data/Run2016H/SingleMuon/NANOAOD/Nano02Dec2019-v1/270000/062790E9-2D36-FF42-9525-BCD698324ED0.root"
    elif dataYear==2017:
        ifileDATA = "data/Run2017F/BTagCSV/NANOAOD/Nano1June2019-v1/40000/030D3C6F-240B-3247-961D-1A7C0922DC1F.root"
    elif dataYear==2018:
        ifileDATA = "data/Run2018B/DoubleMuon/NANOAOD/Nano1June2019-v1/40000/20FCA3B4-6778-7441-B63C-307A21C7C2F0.root"

input_files = []
if isMC:
    if inputFile == '' :     #this will run on the hardcoded file above
        input_files.append( input_dir + ifileMC )
    else: 
        input_files.extend( inputFile.split(',') )
else:
    if inputFile == '' : #this will run on the hardcoded file above     
        input_files.append( input_dir + ifileDATA )
    else : 
        input_files.extend( inputFile.split(',') )

modules = []
if args.runNoModules:
    print("INFO >>> Running with no modules") 
else:
    bob=SequenceBuilder(isMC, dataYear, runPeriod, jesUncert, eraVFP, passall, genOnly, 
                        addOptional=True, 
                        onlyTestModules=isTest, 
                        doSkim=args.doSkim, 
                        runOnlySkim=args.runOnlySkim)
    modules=bob.buildFinalSequence()

# better to use the maxEntries argument of PostProcessor (so that one can use it inside that class)
#treecut = ("Entry$<" + str(maxEvents) if maxEvents > 0 else None)
treecut = None
kd_file = "keep_and_drop"
if isMC:
    kd_file += "_MC"
    if genOnly: kd_file+= "GenOnly"
    elif trigOnly: kd_file+= "TrigOnly"
else:
    kd_file += "_Data"
kd_file += ".txt"
if isTest:
    kd_file = "keep_and_drop_TEST.txt"
if customKeepDrop != "":
    kd_file = customKeepDrop

print "Keep drop file used:", kd_file

if args.condor:

    print 'making a condor setup...'
    os.system('mkdir -p {cd}'.format(cd=args.condorDir))

    ## make sure this goes with xrootd
    xrdindir  = args.dsdir
    if '/eos/cms/store/' in xrdindir and not 'eoscms' in xrdindir:
        xrdindir = 'root://eoscms.cern.ch/'
    if '/eos/user/' in xrdindir and not 'eosuser' in xrdindir: ## works also with eos user        
        xrdindir = 'root://eosuser.cern.ch/'

    skipFiles = getLinesFromFile(args.condorSkipFiles) if args.condorSkipFiles else []
    selectFiles = getLinesFromFile(args.condorSelectFiles) if args.condorSelectFiles else []

    skipFiles   = [i.strip().replace('_Skim','') for i in skipFiles]
    selectFiles = [i.strip().replace('_Skim','') for i in selectFiles]

    ## get the list of files from the given
    listoffiles = []
    for root, dirnames, filenames in os.walk(args.dsdir):
        for filename in filenames:
            if '.root' in filename:
                # note, filename will not have the full path,
                # so 'filename not in skipFiles/selectFiles' won't always work
                # it depends on how files are stored in skipFiles or selectFiles
                # the following works both if they include the full path or only the basename
                if len(skipFiles) and any(filename in str(x) for x in skipFiles): continue
                if len(selectFiles) and all(filename not in str(x) for x in selectFiles): continue
                listoffiles.append(xrdindir+os.path.join(root, filename))

    # shuffle input list, because some input files are much larger than others, and it this way we ensure that the run time is more uniform among different jobs
    random.shuffle(listoffiles) # this modifies the array

    listoffilechunks = []
    for ff in range(len(listoffiles)/args.nfiles+1):
        listoffilechunks.append(listoffiles[ff*args.nfiles:args.nfiles*(ff+1)])

    dm = 'mc' if isMC else 'data'
    runperiod = ''
    if dm == 'data':
        runperiod = runPeriod
    
    # storing list of inputs, can be used to easily resubmit failed jobs based on missing output
    # after checking which one were missing
    listProcessedFiles_filename = "{cd}/inputFiles_{dm}{rp}.txt".format(cd=args.condorDir,dm=dm,rp=runperiod)
    try:
        with open(listProcessedFiles_filename, 'w') as f:
            f.write("\n".join(str(x) for x in listoffiles))
    except IOError as e:
        print("Couldn't open or write to file %s (%s)." % (listProcessedFiles_filename,e))

    makeDummyFile()
    tmp_condor_filename = '{cd}/condor_submit_{dm}{rp}.condor'.format(cd=args.condorDir,dm=dm,rp=runperiod)
    job_desc = '''Executable = dummy_exec.sh
use_x509userproxy = true
getenv      = True
environment = "LS_SUBCWD={here}"
transfer_output_files = ""
request_memory = 2000
transfer_output_files = ""
+MaxRuntime = {t}\n'''.format(here=os.environ['PWD'],t=args.runtime)
    if args.jobname:
        job_desc += '+JobBatchName = "%s"\n' % args.jobname
    # some customization
    if os.environ['USER'] in ['mdunser', 'kelong', 'bendavid']:
        job_desc += '+AccountingGroup = "group_u_CMST3.all"\n'
    if os.environ['USER'] in ['mciprian']:
        job_desc += '+AccountingGroup = "group_u_CMS.CAF.ALCA"\n' 
    ##
    job_desc += '\n'

    tmp_condor = open(tmp_condor_filename,'w')
    tmp_condor.write(job_desc)
    for il,fs in enumerate(listoffilechunks):
        if not len(fs): continue
        flags = ""
        if isMC:
            flags += "--eraVFP {e}".format(e=eraVFP)
        else:
            if runPeriod:
                flags += " --runPeriod {rp}".format(rp=runPeriod)
        if args.doSkim:
            flags += " --doSkim {sk}".format(sk=args.doSkim)
        if args.runOnlySkim:
            flags += " --runOnlySkim"
        if args.noPostfixSkim:
            flags += " --noPostfixSkim"
        if args.compression:
            flags += " --compression {c}".format(c=args.compression)
        if args.runNoModules:
            flags += " --runNoModules"
        if args.customKeepDrop:
            flags += " --customKeepDrop {kd}".format(kd=args.customKeepDrop)
            
        tmp_condor.write('arguments = {od} {pwd}/postproc.py  --isMC {isMC} --dataYear {y} --passall {pa} {flags} -iFile {files}\n'.format(isMC=isMC,y=dataYear, pa=passall, flags=flags, files=','.join(fs),od=outDir,pwd=os.environ['PWD']))
        tmp_condor.write('''
Log        = {cd}/log_condor_{dm}{rp}_chunk{ch}.log
Output     = {cd}/log_condor_{dm}{rp}_chunk{ch}.out
Error      = {cd}/log_condor_{dm}{rp}_chunk{ch}.error\n'''.format(cd=args.condorDir,ch=il,dm=dm,rp=runperiod))
        tmp_condor.write('queue 1\n\n')
    tmp_condor.close()

    print 'condor submission file made:', tmp_condor_filename
    if args.executeCondor:
        print("Executing condor submission file")
        xcmd = "condor_submit " + tmp_condor_filename
        os.system(xcmd)

else:
    p = PostProcessor(outputDir=outDir,  
                      inputFiles=(input_files if crab==0 else inputFiles()),
                      cut=treecut,      
                      modules=modules,
                      provenance=True,
                      outputbranchsel=kd_file,
                      maxEntries=maxEvents if maxEvents>0 else None,
                      fwkJobReport=(False if crab==0 else True),
                      jsonInput=(None if crab==0 else runsAndLumis()),
                      compression=args.compression,
                      saveHistoGenWeights=(True if isMC else False),
                      allowNoPostfix=args.noPostfixSkim
                  )
    p.run()

print "DONE"
#os.system("ls -lR")
