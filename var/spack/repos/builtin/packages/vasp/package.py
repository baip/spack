##############################################################################
# Copyright (c) 2013-2016, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/llnl/spack
# Please also see the NOTICE and LICENSE files for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License (as
# published by the Free Software Foundation) version 2.1, February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################
from spack import *


class Vasp(MakefilePackage):
    """VASP: Vienna Ab-initio Simulation Package"""

    homepage = "https://www.vasp.at/"
    url      = "file:///global/homes/b/baip/tools/vasp.5.4.4.tar.bz2"

    version('5.4.4', 'fbc9e6961fafea3e4f16e5e42e46f7f9')

    depends_on('intel-mkl')

    #def edit(self, spec, prefix):
        # FIXME: Edit the Makefile if necessary
        # FIXME: If not needed delete this function
        # makefile = FileFilter('Makefile')
        # makefile.filter('CC = .*', 'CC = cc')

    parallel = False

    def setup_environment(self, spack_env, run_env):
        spack_env.set('CRAYPE_LINK_TYPE', 'static')
        spack_env.set('INSTALL_DIR', self.prefix)

    def install(self, spec, prefix):
        make('all')
