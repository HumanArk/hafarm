import hou
from optparse import OptionParser
import sys, os
import fileseq

def help():
    return 'harender: Houdinis hrender csh script replacement.\
        \n\tusage: harender [-f "1 100" -i 1 -] -d /out/mantra1 myscene.hip \
        \n Alternatively frame list may be specifid with -l (-l 1-3,4,5,6,7-12x2)'


def parseOptions():
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-d", "--driver", dest="driver",  action="store", type="string", help="ROP driver to render.")
    parser.add_option("-f", "--frame_range", dest="frame_range",  action="store", type="int", nargs=2, help="Frames range to render (-f 1 100)")
    parser.add_option("-i", "--increment", dest="increment",  action="store", type="int", default=1, help="Frames imcrement.")
    parser.add_option("-j", "--threads", dest="threads",  action="store", type="int", default=1, help="Controls multithreading.")
    parser.add_option("-l", "--frame_list", dest="frame_list",  action="store",  help="Alternative ")
    parser.add_option("", "--ignore_tiles", dest='ignore_tiles', action='store_true', default=False, help="Disables tiling on Mantra Rop (This allow custom ifd filtering setup).")
    parser.add_option("", "--generate_ifds", dest='generate_ifds', action='store_true', default=False, help="Changes Rop setting to save IFD files on disk. ")
    parser.add_option("", "--ifd_path", dest='ifd_path', action='store', default='$JOB/render/sungrid/ifd', help="Overwrites default IFD path.")
    (opts, args) = parser.parse_args(sys.argv[1:])
    return opts, args



def main():
    """Replacement for Houdini's own hrender script. Basic functions for rendering specified rop. 
       Main difference (reason to replace  hrender) was to allow rendring a list of randomly selected frames.
    """

    options, args     = parseOptions()

    if len(sys.argv) < 3:
        print help()
        sys.exit()


    # As we keep similarity to hredner, 
    # last argument of command line is a hip file. 
    scene_file = sys.argv[-1]

    print options, args
    #sys.exit()

    # Catch errors:
    if not os.path.isfile(scene_file):
        print "Can't find %s scene file." % scene_file
        return 1
    try:
        hou.hipFile.load(scene_file, True, True)
    except:
        print "Can't open %s" % scene_file
        sys.exit()
    try:
        driver = hou.node(options.driver)
    except:
        print "Can't find %s rop" % options.driver
        sys.exit()

    # Ignoring tiling:
    if options.ignore_tiles and driver.parm("vm_tile_render"):
        driver.parm("vm_tile_render").set(0)

    # Change ROP to save IFD to disk:
    if driver.type().name() == 'ifd' and options.generate_ifds:
        driver.parm("soho_outputmode").set(1)
        scene_path, scene_name = os.path.split(hou.hipFile.name())
        scene_name, ext = os.path.splitext(scene_name)
        ifd_name = os.path.join(options.ifd_path, scene_name + ".$F.ifd")
        driver.parm('soho_diskfile').set(ifd_name)


    # Render with all details specified in a hip file:
    if not options.frame_list:
        frame_range = tuple(options.frame_range + (options.increment,))
        driver.render(frame_range=frame_range, ignore_inputs=True, verbose=True)
    # Or render from a list of random frames:
    else:
        for frame in fileseq.FrameSet(options.frame_list):
            driver.render(frame_range=(frame, frame), ignore_inputs=True, verbose=True)
        

if __name__ == '__main__': main()