##############################################################################
# Copyright (c) 2013-2017, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/spack/spack
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
import os
import shutil
import copy

from spack import *


class Cp2k(Package):
    """CP2K is a quantum chemistry and solid state physics software package
    that can perform atomistic simulations of solid state, liquid, molecular,
    periodic, material, crystal, and biological systems
    """
    homepage = 'https://www.cp2k.org'
    url = 'https://sourceforge.net/projects/cp2k/files/cp2k-3.0.tar.bz2'
    list_url = 'https://sourceforge.net/projects/cp2k/files/'

    version('5.1', 'f25cf301aec471d7059179de4dac3ee7')
    version('4.1', 'b0534b530592de15ac89828b1541185e')
    version('3.0', 'c05bc47335f68597a310b1ed75601d35')

    variant('static', default=True, description='Favor static over dynamic linking')
    variant('mpi', default=True, description='Enable MPI support')
    variant('smm', default='libxsmm', values=('libxsmm', 'libsmm', 'none'),
            description='Library for small matrix multiplications')
    variant('plumed', default=False, description='Enable PLUMED support')

    depends_on('python', type='build')

    depends_on('lapack~shared', when='+static')
    depends_on('lapack+shared', when='~static')
    depends_on('blas~shared', when='+static')
    depends_on('blas+shared', when='~static')
    depends_on('fftw@3:')
    depends_on('libint@1.1.4:1.2', when='@3.0:5.999')
    depends_on('libxsmm', when='smm=libxsmm')
    depends_on('libxc@2.2.2:')

    depends_on('mpi@2:', when='+mpi')
    depends_on('scalapack~shared', when='+mpi+static')
    depends_on('scalapack+shared', when='+mpi~static')
    depends_on('elpa@2011.12:2016.13', when='+mpi')
    depends_on('pexsi+fortran@0.9.0:0.9.999', when='+mpi@:4.999')
    depends_on('pexsi+fortran@0.10.0:', when='+mpi@5.0:')
    depends_on('plumed+mpi', when='+plumed+mpi')
    depends_on('plumed~mpi', when='+plumed~mpi')

    # Apparently cp2k@4.1 needs an "experimental" version of libwannier.a
    # which is only available contacting the developer directly. See INSTALL
    # in the stage of cp2k@4.1
    depends_on('wannier90', when='@3.0+mpi')

    # TODO : add dependency on CUDA

    def with_static(self, query):
        if '~static' in self.spec:
            return query
        elif ':' in query:
            return query + ',static'
        else:
            return query + ':static'

    def install(self, spec, prefix):
        # Construct a proper filename for the architecture file
        cp2k_architecture = '{0.architecture}-{0.compiler.name}'.format(spec)
        cp2k_version = 'sopt' if '~mpi' in spec else 'popt'
        makefile_basename = '.'.join([cp2k_architecture, cp2k_version])
        makefile = join_path('arch', makefile_basename)

        # Write the custom makefile
        with open(makefile, 'w') as mkf:
            # Optimization flags
            optflags = {
                'gcc': [
                    '-O2',
                    '-mtune=native',
                    '-funroll-loops',
                    '-ffast-math',
                    '-ftree-vectorize',
                ], 'intel': [
                    '-O2',
                    '-ip',
                    '-pc64',
                    '-unroll',
                ]
            }

            dflags = [
                '-D__DATA_DIR=' + self.prefix.data,
                '-DNDEBUG',
                '-D__FFTW3',
                '-D__LIBINT',
                '-D__LIBINT_MAX_AM=6',
                '-D__LIBDERIV_MAX_AM1=5',
                '-D__LIBXC',
            ]

            if '^intel-mkl' in spec:
                dflags.append('-D__FFTSG')

            cppflags = []

            cflags = copy.deepcopy(optflags[self.spec.compiler.name])
            cxxflags = copy.deepcopy(optflags[self.spec.compiler.name])
            fcflags = copy.deepcopy(optflags[self.spec.compiler.name])

            if '%intel' in spec:
                dflags.extend([
                    '-D__INTEL',
                    '-D__HAS_ISO_C_BINDING',
                    '-D__USE_CP2K_TRACE',
                    '-D__MKL'
                ])
                cflags.append('-fp-model precise')
                cxxflags.append('-fp-model precise')
                fcflags.extend([
                    '-fp-model source',
                    '-heap-arrays 64',
                    '-diag-disable 8290,8291,10010,10212,11060',
                    '-free',
                    '-fpp'
                ])
            elif '%gcc' in spec:
                fcflags.extend(['-ffree-form', '-ffree-line-length-none'])

            fftw = spec[self.with_static('fftw')]
            libxc = spec[self.with_static('libxc:fortran')]

            fcflags.extend([fftw.headers.cpp_flags, libxc.headers.cpp_flags])

            fftw = fftw.libs
            libxc = libxc.libs

            # LAPACK / BLAS
            lapack = spec[self.with_static('lapack')].libs
            blas = spec[self.with_static('blas')].libs

            ldflags = [(fftw + lapack + blas + libxc).search_flags]

            libs = spec[self.with_static('libint')].libs

            # MPI
            if '+mpi' in self.spec:
                if '^mpi@3:' in spec:
                    dflags.append('-D__MPI_VERSION=3')
                elif '^mpi@2:' in spec:
                    dflags.append('-D__MPI_VERSION=2')

                dflags.extend([
                    '-D__parallel',
                    '-D__LIBPEXSI',
                    '-D__SCALAPACK'
                ])

                elpa = spec[self.with_static('elpa')]
                if spec.satisfies('@:4.999'):
                    if elpa.satisfies('@:2014.5.999'):
                        dflags.append('-D__ELPA')
                    elif elpa.satisfies('@2014.6:2015.10.999'):
                        dflags.append('-D__ELPA2')
                    else:
                        dflags.append('-D__ELPA3')
                else:
                    dflags.append('-D__ELPA={0}{1:02d}'.format(
                        elpa.version[0], int(elpa.version[1])))
                    fcflags.append('-I' + join_path(
                        elpa.prefix, 'include',
                        'elpa-{0}'.format(str(elpa.version)), 'elpa'
                    ))

                pexsi = spec['pexsi']
                fcflags.extend([
                    # spec['elpa:fortran'].headers.cpp_flags
                    '-I' + join_path(
                        elpa.prefix,
                        'include',
                        'elpa-{0}'.format(str(elpa.version)),
                        'modules'
                    ),
                    # spec[pexsi:fortran].headers.cpp_flags
                    '-I' + join_path(pexsi.prefix, 'fortran')
                ])

                scalapack = spec[self.with_static('scalapack')].libs
                ldflags.append(scalapack.search_flags)

                libs += (
                    elpa.libs +
                    pexsi.libs +
                    spec['superlu-dist'].libs +
                    spec['parmetis'].libs +
                    spec['metis'].libs +
                    scalapack +
                    self.spec[self.with_static('mpi:cxx')].libs +
                    self.compiler.stdcxx_libs
                )

                if 'superlu-dist@4.3' in spec:
                    ldflags = ['-Wl,--allow-multiple-definition'] + ldflags

                if 'wannier90' in spec:
                    dflags.append('-D__WANNIER90')
                    wannier = join_path(
                        spec['wannier90'].prefix.lib, 'libwannier.a'
                    )
                    libs += LibraryList(wannier)

            if 'smm=libsmm' in spec:
                try:
                    libsmm_path = env['LIBSMM_PATH']
                except KeyError:
                    raise KeyError('Point environment variable LIBSMM_PATH to '
                                   'the absolute path of the libsmm.a file')
                if not os.path.isfile(libsmm_path):
                    raise IOError('The file LIBSMM_PATH pointed to does not '
                                  'exist. Note that it must be absolute path.')
                dflags.extend([
                    '-D__HAS_smm_dnn',
                    '-D__HAS_smm_vec',
                ])
                libs += LibraryList(libsmm_path)
            elif 'smm=libxsmm' in spec:
                dflags.append('-D__LIBXSMM')
                fcflags.append(spec['libxsmm'].headers.cpp_flags)
                libxsmm = spec['libxsmm'].libs
                ldflags.append(libxsmm.search_flags)
                libs += libxsmm

            if '+plumed' in self.spec:
                plumed = spec['plumed']
                # Include Plumed.inc in the Makefile
                mkf.write('include {0}\n\n'.format(
                    join_path(plumed.prefix.lib,
                              'plumed',
                              'src',
                              'lib',
                              'Plumed.inc')
                ))
                # Add required macro
                dflags.append('-D__PLUMED2')
                libs += plumed.libs

            libs += (libxc + fftw + lapack + blas)

            mkf.write('CC = {0.compiler.cc}\n'.format(self))

            if '%intel' in self.spec:
                # CPP is a commented command in Intel arch of CP2K
                # This is the hack through which cp2k developers avoid doing :
                #
                # ${CPP} <file>.F > <file>.f90
                #
                # and use `-fpp` instead
                mkf.write('CPP = # {0.compiler.cc} -P\n'.format(self))
                mkf.write('AR = xiar -r\n')
            else:
                mkf.write('CPP = # {0.compiler.cc} -E\n'.format(self))
                mkf.write('AR = ar -r\n')

            fc = self.compiler.fc if '~mpi' in spec else self.spec['mpi'].mpifc
            mkf.write('FC = {0}\n'.format(fc))
            mkf.write('LD = {0}\n\n'.format(fc))

            cppflags.extend(dflags)
            cflags.extend(cppflags)
            cxxflags.extend(cppflags)
            fcflags.extend(cppflags)

            # Write compiler flags to file
            mkf.write('DFLAGS = {0}\n\n'.format(' '.join(dflags)))
            mkf.write('CPPFLAGS = {0}\n\n'.format(' '.join(cppflags)))
            mkf.write('CFLAGS = {0}\n\n'.format(' '.join(cflags)))
            mkf.write('CXXFLAGS = {0}\n\n'.format(' '.join(cxxflags)))
            mkf.write('FCFLAGS = {0}\n\n'.format(' '.join(fcflags)))
            mkf.write('LDFLAGS = {0}\n\n'.format(' '.join(ldflags)))
            if '%intel' in spec:
                mkf.write('LDFLAGS_C = {0}\n\n'.format(
                    ' '.join(ldflags) + ' -nofor_main')
                )
            mkf.write('LIBS = {0}\n\n'.format(' '.join(libs)))

        with working_dir('makefiles'):
            # Apparently the Makefile bases its paths on PWD
            # so we need to set PWD = os.getcwd()
            pwd_backup = env['PWD']
            env['PWD'] = os.getcwd()
            make('ARCH={0}'.format(cp2k_architecture),
                 'VERSION={0}'.format(cp2k_version))
            env['PWD'] = pwd_backup
        exe_dir = join_path('exe', cp2k_architecture)
        shutil.copytree(exe_dir, self.prefix.bin)
        shutil.copytree('data', self.prefix.data)
