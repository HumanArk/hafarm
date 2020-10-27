import os
import nukescripts, nuke

class FakePythonPanel(object):
    pass


if 'PythonPanel' not in nukescripts.__dict__:
    nukescripts.PythonPanel = FakePythonPanel
from uuid import uuid4
import utils
from HaGraph import HaGraph
from HaGraph import HaGraphItem
from hafarm import SlurmRender



class HaContextNuke(object):
    def _get_graph(self, **kwargs):
        job = os.getenv('JOB_CURRENT', 'none')

        write_node_list = self._write_node_list()

        proxy = nuke.root().knob('proxy').value() 
        if proxy == True:
            for write_node in write_node_list:
                if write_node.knob('proxy').value() == "":
                    err = 'You must specify a proxy file name to write in "%s" node' % write_node.name()
                    raise Exception(err)

        nuke.scriptSave()
        graph = HaGraph(graph_items_args=[])
        if not 'target_list' in kwargs:
            kwargs['target_list'] = [x.name() for x in write_node_list ]

        if not 'output_picture' in kwargs:
            kwargs['output_picture'] = str(nuke.root().node(kwargs['target_list'][0]).knob('file').getEvaluatedValue())

        graph.add_node(NukeWrapper(**kwargs))
        return graph


    def _queue_list(self):
        return ('3d', 'nuke', 'turbo_nuke', 'dev')


    def _group_list(self):
        return ('allhosts', 'grafika', 'render', 'old_intel', 'new_intel')


    def _write_node_list(self):
        return  [ node for node in nuke.root().selectedNodes() if node.Class() in ('Write',) ]





class NukeWrapper(HaGraphItem):
    def __init__(self, *args, **kwargs):
        index, name = str(uuid4()), 'nuke'
        tags, path = ('/nuke/farm', '')
        dependencies = []
        super(NukeWrapper, self).__init__(index, dependencies, name, path, tags, *args, **kwargs)
        version = str(nuke.NUKE_VERSION_MAJOR) + '.' + str(nuke.NUKE_VERSION_MINOR)
        self.parms['exe'] = 'Nuke%s' % version
        self.parms['command_arg'] = ['-x -V ']
        self.parms['target_list'] = kwargs['target_list']
        write_node = self.parms['target_list'][0]
        script_name = str(nuke.root().name())
        path, name = os.path.split(script_name)
        self.parms['scene_file'] << { 'scene_fullpath': script_name }
        self.parms['job_name'] << { "job_basename": name
                                    , "jobname_hash": self.get_jobname_hash()
                                    , "render_driver_name": str(nuke.root().node(write_node).name()) }
        self.parms['req_license'] = 'nuke_lic=1'
        self.parms['step_frame'] = 5
        self.parms['ignore_check'] = True
        self.parms['queue'] = kwargs['queue']
        self.parms['group'] = kwargs['group']
        self.parms['start_frame'] = kwargs['start_frame']
        self.parms['end_frame'] = kwargs['end_frame']
        self.parms['frame_range_arg'] = ['-F %s-%sx%s',
                                         'start_frame',
                                         'end_frame', kwargs['frame_range']]
        
        self.parms['output_picture'] = kwargs['output_picture']
        self.parms['job_on_hold'] = kwargs['job_on_hold']
        self.parms['priority'] = kwargs['priority']

        if 'email_list' in kwargs:
            self.parms['email_list'] = [utils.get_email_address()]
            self.parms['email_opt'] = 'eas'

        if 'req_resources' in kwargs:
            self.parms['req_resources'] = kwargs['req_resources']

        if self.parms['target_list']:
            self.parms['command_arg'] += [' -X %s ' % ' '.join(self.parms['target_list'])]


class NukeFarmGUI(nukescripts.PythonPanel):
    _ctx = HaContextNuke()

    def __init__(self):
        nukescripts.PythonPanel.__init__(self, 'NukeFarmGUI', 'com.human-ark.NukeFarmGUI')
        self.setMinimumSize(100, 400)
        self.initGUI()


    def run(self):
        result = nukescripts.PythonPanel.showModalDialog(self)
        if not result:
            return

        write_node = self._ctx._write_node_list()[0]

        global_params = dict(
             queue = str(self.queueKnob.value())
            ,group = str(self.group_list.value())
            ,start_frame = int(self.start_frame.getValue())
            ,end_frame = int(self.end_frame.getValue())
            ,frame_range = int(self.every_of_Knob.getValue())
            ,target_list = self.write_name.value().split()
            ,output_picture = str(write_node.knob('file').getEvaluatedValue())
            ,job_on_hold = bool(self.hold_Knob.value())
            ,priority = int(self.priorityKnob.value())
        )
        
        if self.requestSlots_Knob.value():
            global_params.update( {'req_resources': 'procslots=%s' % int(self.slotsKnob.value()) } )
        
        # if self.email_Knob.value():
        #     global_params.update( {'email_list': [utils.get_email_address()]} )
        
        graph = self._ctx._get_graph(**global_params)
        graph.set_render(SlurmRender.SlurmRender)
        graph.render()
        return True


    def initGUI(self):
        import os
        self.queueKnob = nuke.Enumeration_Knob('queue', 'Queue:', self._ctx._queue_list())
        self.queueKnob.setTooltip('Queue to submit job to.')
        self.queueKnob.setValue('nuke')
        self.addKnob(self.queueKnob)
        self.group_list = nuke.Enumeration_Knob('group', 'Host Group:', self._ctx._group_list() )
        self.group_list.setTooltip('Host group to submit job to.')
        # FUx for super old cpus 
        if nuke.NUKE_VERSION_MAJOR > 11:
            self.group_list.setValue('new_intel')
        else:
            self.group_list.setValue('allhosts')
        self.addKnob(self.group_list)
        self.maxTasks_Knob = nuke.WH_Knob('max_tasks', 'Maximum tasks:')
        self.maxTasks_Knob.setTooltip('Maximum number of tasks running on farm at once.')
        self.maxTasks_Knob.setValue(10)
        self.addKnob(self.maxTasks_Knob)
        self.separator5 = nuke.Text_Knob('')
        self.addKnob(self.separator5)
        write_name = ' '.join( [x.name() for x in self._ctx._write_node_list() ] )
        self.write_name = nuke.String_Knob('write_name', 'Write nodes:')
        self.write_name.setTooltip('Write nodes selected to rendering (empty for all Writes in a scene)')
        self.addKnob(self.write_name)
        self.write_name.setValue(write_name)
        self.separator2 = nuke.Text_Knob('')
        self.addKnob(self.separator2)
        self.requestSlots_Knob = nuke.Boolean_Knob('request_slots', 'Request Slots')
        self.requestSlots_Knob.setTooltip("Normally Nuke doesn't require free slots on the farm, which causes instant start of rendering            for a cost of potentially slower renders in over-loaded conditions. This is because, unlike 3d renderes, Nuke is often limited             by network access, not CPU power. The toggle forces Nuke to behave like 3d renderer and run only on a machine             where free slots (cores) are avaiable. It will eventually run faster, but will have to wait in a queue for free resources.             You may try to set the slots number lower (4 for example) while toggling that on.")
        self.addKnob(self.requestSlots_Knob)
        self.slotsKnob = nuke.WH_Knob('slots', 'Slots:')
        self.slotsKnob.setTooltip('Maximum number of threads to use by Nuke.')
        self.slotsKnob.setValue(15)
        self.addKnob(self.slotsKnob)
        self.priorityKnob = nuke.WH_Knob('priority', 'Priority:')
        self.priorityKnob.setTooltip("Set render priority (set lower value if you want to down grade your own renders, to control            which from your submited jobs are prioritized (as you can't overwrite others prority, you are about only to prioritize your own.")
        self.priorityKnob.setRange(-1023, 1024)
        self.priorityKnob.setValue(-500)
        self.addKnob(self.priorityKnob)
        self.stepKnob = nuke.WH_Knob('steps', 'Render step:')
        self.stepKnob.setTooltip('Number of frames in a single batch. Lower value means more throughput on the farm, and fair share of resources,             for a little exapnse of time.')
        self.stepKnob.setValue(5)
        self.addKnob(self.stepKnob)
        self.separator3 = nuke.Text_Knob('')
        self.addKnob(self.separator3)
        self.start_frame = nuke.Int_Knob('start_frame', 'Start Frame:')
        self.addKnob(self.start_frame)
        self.start_frame.setValue(int(nuke.root().knob('first_frame').getValue()))
        self.end_frame = nuke.Int_Knob('end_frame', 'End Frame:')
        self.addKnob(self.end_frame)
        self.end_frame.setValue(int(nuke.root().knob('last_frame').getValue()))
        self.every_of_Knob = nuke.WH_Knob('every_of', 'Render every:')
        self.every_of_Knob.setTooltip('Render only the n-th frame in a row.')
        self.every_of_Knob.setValue(1)
        self.addKnob(self.every_of_Knob)
        self.separator4 = nuke.Text_Knob('')
        self.addKnob(self.separator4)
        self.hold_Knob = nuke.Boolean_Knob('hold', 'Submit job on hold')
        self.hold_Knob.setTooltip("Job won't start unless manually unhold in qmon.")
        self.addKnob(self.hold_Knob)
        # self.email_Knob = nuke.Boolean_Knob('email', 'Send me mail when finished')
        # self.email_Knob.setTooltip('Sends an email for every finised/aborded task.')
        # self.addKnob(self.email_Knob)
        self.separator5 = nuke.Text_Knob('')
        self.addKnob(self.separator5)
        self.proxy_Knob = nuke.Boolean_Knob('proxy', 'Render proxy')
        self.proxy_Knob.setValue(nuke.root().knob('proxy').value())
        self.addKnob(self.proxy_Knob)


    def knobChanged(self,knob):
        if nuke.thisKnob().name() == 'proxy':
            nuke.root().knob('proxy').setValue(knob.value())