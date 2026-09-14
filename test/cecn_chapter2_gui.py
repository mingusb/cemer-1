#!/usr/bin/env python3
"""Exercise real chapter 2 GUI controls on an isolated 1600x1000 X11 desktop.

Uses mouse/keyboard actions for native task buttons and parameter edits. The
application server only observes results and bounds the spike/rate experiment.
Screenshots retain the offline wiki, native 3D views and scientific plots.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

from inductor_head_gui_regression import GuiCase, GuiServer, capture_screenshot
from modern_stack_regressions import REPO, require
from cecn_chapter2_regressions import FIXTURES, scalars


class ChapterGUI(GuiServer):
    def window(self):
        return self.xdotool('search','--all','--onlyvisible','--pid',self.process.pid,
                            '--name','projects.*'+self.case.directory.name).splitlines()[0]

    def click(self, name, x, y):
        self.transcript.write(json.dumps({'actual_gui_click':name,'x':x,'y':y})+'\n');self.transcript.flush()
        self.xdotool('windowactivate','--sync',self.window())
        self.xdotool('mousemove',x,y,'click',1)
        time.sleep(.15)

    def wait_state(self, expected):
        deadline=time.monotonic()+self.case.args.timeout
        while time.monotonic()<deadline:
            require(self.process.poll() is None,'GUI process exited during task')
            if int(self.call('GetRunState'))==expected:return
            time.sleep(.05)
        raise TimeoutError('native GUI task did not reach state '+str(expected))

    def done(self):
        deadline=time.monotonic()+self.case.args.timeout
        while time.monotonic()<deadline:
            require(self.process.poll() is None,'GUI process exited during task')
            if int(self.call('GetRunState'))==0:return
            time.sleep(.05)
        raise TimeoutError('native GUI task did not finish')

    def values(self, table, column):
        return self.call('GetData',table=table,column=column)['columns'][0]['values']

    def screenshot(self, name):
        # Native tab switches and 3D/document paints complete asynchronously.
        time.sleep(.5)
        capture_screenshot(self.case.directory/(name+'.png'))

    def save(self):
        self.xdotool('windowactivate','--sync',self.window())
        self.transcript.write(json.dumps({'actual_gui_key':'Ctrl+S'})+'\n');self.transcript.flush()
        self.xdotool('key','--clearmodifiers','ctrl+s')
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            digest=hashlib.sha256(self.case.fixture.read_bytes()).hexdigest()
            if digest != self.case.original_digest:
                self.case.equal('native_keyboard_save_changes_artifact',digest!=self.case.original_digest,True)
                return
            time.sleep(.1)
        raise TimeoutError('Ctrl+S did not save the changed project')


def neuron(case, server):
    server.click('ControlPanel tab',605,151)
    server.screenshot('02-controls')
    server.click('Defaults',509,752);server.done()
    server.click('Init',330,752);server.done()
    server.click('Step Cycle',428,752);server.wait_state(3)
    case.equal('actual_step_cycle_pauses',int(server.call('GetRunState')),3)
    server.click('Run',344,752);server.done()
    base_spikes=sum(server.values('CycleOutputData','spike'))
    case.equal('native_run_200_cycles',len(server.values('CycleOutputData','cycle')),200)
    case.equal('native_run_spikes',base_spikes>0,True)
    server.click('CycleOutputData plot tab',918,151)
    server.screenshot('03-spikes-and-adaptation')
    server.click('KNa adaptation checkbox',333,470)
    server.click('Apply',632,785)
    server.click('Init',304,752);server.done()
    server.click('Run',344,752);server.done()
    no_adapt=sum(server.values('CycleOutputData','spike'))
    case.equal('actual_adaptation_control_increases_firing_when_disabled',no_adapt>base_spikes,True)
    for channel in ['gc_kna_f','gc_kna_m','gc_kna_s']:
        case.equal('actual_adaptation_control_'+channel,max(server.values('CycleOutputData',channel)),0.0)
    server.screenshot('04-adaptation-disabled')
    server.click('Init',304,752);server.done()
    server.click('Run before Stop',344,752)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        if len(server.values('CycleOutputData','cycle'))>0:break
        time.sleep(.02)
    server.click('Stop',480,752)
    case.equal('actual_stop_state',int(server.call('GetRunState')),3)
    stopped_rows=len(server.values('CycleOutputData','cycle'))
    case.equal('actual_stop_before_completion',0<stopped_rows<200,True)
    server.screenshot('05-stopped')
    server.click('Run resumes',344,752);server.done()
    case.equal('actual_resume_completes_200_cycles',len(server.values('CycleOutputData','cycle')),200)
    server.click('Defaults restores parameters',534,752);server.done()
    for key,value in {'g_bar_e_start':.125,'g_bar_e_end':.625,'g_bar_e_inc':.125,'n_samples':1,'noise_var':0}.items():
        server.set_variable('SpikeVsRate',key,value)
    server.click('SpikeVsRate Run',625,752);server.done()
    case.equal('actual_spike_rate_button_input_grid',server.values('.programs[1].objs[0]','g_bar_e'),[.125,.25,.375,.5,.625])
    server.click('SpikeVsRate plot tab',1027,151)
    server.screenshot('06-spike-rate-plot')
    server.console('taMisc::ConsoleOutput("CH2_GUI_CSS42 " + String(6*7));','CH2_GUI_CSS42 42')
    case.equal('typed_css_arithmetic','42','42')
    server.save()


def detector(case, server):
    server.click('ControlPanel tab',605,131)
    server.screenshot('02-controls')
    server.click('Init',455,735);server.done()
    server.click('Step Trial',527,735);server.wait_state(3)
    case.equal('actual_step_trial_presents_zero',server.values('TrialOutputData','trial_name'),['0'])
    case.equal('actual_step_trial_pauses',int(server.call('GetRunState')),3)
    server.screenshot('03-step-first-digit')
    server.click('Run completes epoch',390,735);server.done()
    names=server.values('TrialOutputData','trial_name');base=scalars(server.values('TrialOutputData','act'))
    case.equal('native_run_all_digits',names,list(map(str,range(10))))
    case.equal('native_run_selects_digit8',[i for i,x in enumerate(base) if x>.5],[8])
    server.click('Edit g_bar.l',319,242)
    server.xdotool('key','--clearmodifiers','Home','shift+End','BackSpace')
    server.xdotool('type','--clearmodifiers','--delay',20,'1.8')
    server.xdotool('key','--clearmodifiers','Tab')
    server.click('Apply',709,767)
    server.console('LeabraUnitSpec* ch2_gui_spec=.projects[0].networks[0].specs["LeabraUnitSpec_0"]; taMisc::ConsoleOutput("CH2_GUI_LEAK " + String(ch2_gui_spec->g_bar.l));','CH2_GUI_LEAK 1.8')
    case.equal('actual_leak_parameter_edit',1.8,1.8)
    server.click('Run altered leak',390,735);server.done()
    response=scalars(server.values('TrialOutputData','act'))
    case.equal('native_leak_control_broadens_response',[i for i,x in enumerate(response) if x>.5],[5,8])
    case.equal('native_leak_control_preserves_preference',max(range(10),key=response.__getitem__),8)
    server.click('TrialOutputData graph tab',1068,131)
    server.screenshot('04-leak-response-plot')
    server.console('taMisc::ConsoleOutput("CH2_GUI_CSS42 " + String(6*7));','CH2_GUI_CSS42 42')
    case.equal('typed_css_arithmetic','42','42')
    server.save()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,default=REPO/'tools/run-emergent')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=90)
    args=parser.parse_args()
    display=os.environ.get('DISPLAY','')
    if not display or display.rsplit(':',1)[-1] in {'0','0.0'}:
        parser.error('Use a dedicated Xvfb display such as DISPLAY=:93; never the user desktop.')
    os.environ['QT_QPA_PLATFORM']='xcb'
    require(subprocess.check_output(['xdotool','getdisplaygeometry'],text=True).strip()=='1600 1000','GUI replay requires1600x1000 desktop')
    args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=False);args.binary=args.binary.resolve()
    prefix=Path(os.environ.get('EMERGENT_PREFIX_DIR',str(REPO/'install')))
    paths=[prefix/'bin/emergent',prefix/'lib/libtemt.so',prefix/'lib/libemergentlib.so']
    hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    report={'status':'PASS','display':display,'installed_sha256':hashes,'cases':[]}
    for name, task in [('neuron',neuron),('detector',detector)]:
        case=GuiCase(args,name);case.fixture=case.directory/(name+'.proj');shutil.copy2(FIXTURES/(name+'.proj'),case.fixture)
        case.original_digest=hashlib.sha256(case.fixture.read_bytes()).hexdigest()
        row={'name':name,'status':'PASS','checks':case.checks};report['cases'].append(row)
        try:
            with ChapterGUI(case) as server:
                time.sleep(2)
                server.screenshot('01-offline-author-wiki')
                task(case,server)
        except Exception as error:row.update(status='FAIL',error=str(error),traceback=traceback.format_exc());report['status']='FAIL'
    for path,digest in hashes.items():require(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,'installed library changed during GUI test')
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],args.output/'report.json',flush=True)
    return report['status']!='PASS'


if __name__=='__main__':sys.exit(main())
