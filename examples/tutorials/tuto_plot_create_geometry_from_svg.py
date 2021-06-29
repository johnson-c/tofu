"""
Creating a geometry with Inkscape
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a tutorial that shows you how to draw a geometry in Inkscape
and load it in tofu.
"""

###############################################################################
# To see a tutorial on how to draw a vessel's geometry on Inkscape and save
# it to a `svg` file, you can check the video below. Basically, you just need
# to use straight *Bezier curves* to draw the closed polygons that will define
# the vessel and optionally the structures. To define a PFC structure, just
# add a fill color.

###############################################################################

###############################################################################
# .. raw:: html
#
#    <div class="text-center">
#    <iframe width="560" height="315"
#    src="https://www.youtube.com/embed/BoZh2U7I8-g"
#    title="YouTube video player"
#    frameborder="0" allow="accelerometer; autoplay; clipboard-write;
#    encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
#    </iframe>
#    </div>

###############################################################################
# Now, on how to load it and use it in tofu (also shown in the video). We start
# by importing `tofu`.

import tofu as tf

###############################################################################
# `tofu` provides a geometry helper function that allows creating a
# configuration from a `svg` file. Supposing you saved it in a file named
# `"myfirstgeom.svg"`, do
config = tf.geom.Config.from_svg("myfirstgeom.svg", Name="Test", Exp="Test")

###############################################################################
# It already gives you some information on what you loaded, but to see what it
# actually contains:
print(config)

###############################################################################
# To plot it, simply do
config.plot()

###############################################################################
# We can see that the z- and r-axis might not be exactly what we wanted. We
# might also want to adjust the scale. Tofu let's fix those parameters
# when loading the configuration.
config = tf.geom.Config.from_svg("myfirstgeom.svg", Name="Test", Exp="Test",
                                 z0=-140,
                                 r0=10,
                                 scale=0.5
                                 )
config.plot()
import matplotlib.pyplot as plt
plt.show()
