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
from spack import *


class Fftw(AutotoolsPackage):
    """FFTW is a C subroutine library for computing the discrete Fourier
       transform (DFT) in one or more dimensions, of arbitrary input
       size, and of both real and complex data (as well as of even/odd
       data, i.e. the discrete cosine/sine transforms or DCT/DST). We
       believe that FFTW, which is free software, should become the FFT
       library of choice for most applications."""

    homepage = "http://www.fftw.org"
    url      = "http://www.fftw.org/fftw-3.3.4.tar.gz"
    list_url = "http://www.fftw.org/download.html"

    version('3.3.7', '0d5915d7d39b3253c1cc05030d79ac47')
    version('3.3.6-pl2', '927e481edbb32575397eb3d62535a856')
    version('3.3.5', '6cc08a3b9c7ee06fdd5b9eb02e06f569')
    version('3.3.4', '2edab8c06b24feeb3b82bbb3ebf3e7b3')
    version('2.1.5', '8d16a84f3ca02a785ef9eb36249ba433')

    patch('pfft-3.3.5.patch', when="@3.3.5:+pfft_patches", level=0)
    patch('pfft-3.3.4.patch', when="@3.3.4+pfft_patches", level=0)
    patch('pgi-3.3.6-pl2.patch', when="@3.3.6-pl2%pgi", level=0)

    variant(
        'float', default=True,
        description='Produces a single precision version of the library')
    variant(
        'double', default=True,
        description='Produces a double precision version of the library')
    variant(
        'long_double', default=True,
        description='Produces a long double precision version of the library')
    variant(
        'quad', default=False,
        description='Produces a quad precision version of the library '
                    '(works only with GCC and libquadmath)')
    variant('openmp', default=False, description="Enable OpenMP support.")
    variant('mpi', default=True, description='Activate MPI support')
    variant(
        'pfft_patches', default=False,
        description='Add extra transpose functions for PFFT compatibility')

    depends_on('mpi', when='+mpi')
    depends_on('automake', type='build', when='+pfft_patches')
    depends_on('autoconf', type='build', when='+pfft_patches')
    depends_on('libtool', type='build', when='+pfft_patches')

    @property
    def libs(self):
        shared = False if 'static' in self.spec.last_query.extra_parameters else True
        result = find_libraries(['libfftw3'], root=self.prefix,
                                shared=shared, recurse=True)
        return result

    def autoreconf(self, spec, prefix):
        if '+pfft_patches' in spec:
            autoreconf = which('autoreconf')
            autoreconf('-ifv')

    def configure(self, spec, prefix):
        # Base options
        options = [
            '--prefix={0}'.format(prefix),
            '--enable-shared',
            '--enable-threads'
        ]
        if not self.compiler.f77 or not self.compiler.fc:
            options.append("--disable-fortran")
        if spec.satisfies('@:2'):
            options.append('--enable-type-prefix')

        # Variants that affect every precision
        if '+openmp' in spec:
            # Note: Apple's Clang does not support OpenMP.
            if spec.satisfies('%clang'):
                ver = str(self.compiler.version)
                if ver.endswith('-apple'):
                    raise InstallError("Apple's clang does not support OpenMP")
            options.append('--enable-openmp')
            if spec.satisfies('@:2'):
                # TODO: libtool strips CFLAGS, so 2.x libxfftw_threads
                #       isn't linked to the openmp library. Patch Makefile?
                options.insert(0, 'CFLAGS=' + self.compiler.openmp_flag)
        if '+mpi' in spec:
            options.append('--enable-mpi')

        # SIMD support
        # TODO: add support for more architectures
        float_options = []
        double_options = []
        if 'x86_64' in spec.architecture and spec.satisfies('@3:'):
            float_options.append('--enable-sse2')
            double_options.append('--enable-sse2')

        configure = Executable('../configure')

        # Build double/float/long double/quad variants
        if '+double' in spec:
            with working_dir('double', create=True):
                configure(*(options + double_options))
        if '+float' in spec:
            with working_dir('float', create=True):
                configure('--enable-float', *(options + float_options))
        if spec.satisfies('@3:+long_double'):
            with working_dir('long-double', create=True):
                configure('--enable-long-double', *options)
        if spec.satisfies('@3:+quad'):
            with working_dir('quad', create=True):
                configure('--enable-quad-precision', *options)

    def build(self, spec, prefix):
        if '+double' in spec:
            with working_dir('double'):
                make()
        if '+float' in spec:
            with working_dir('float'):
                make()
        if '+long_double' in spec:
            with working_dir('long-double'):
                make()
        if '+quad' in spec:
            with working_dir('quad'):
                make()

    def check(self):
        spec = self.spec
        if '+double' in spec:
            with working_dir('double'):
                make("check")
        if '+float' in spec:
            with working_dir('float'):
                make("check")
        if '+long_double' in spec:
            with working_dir('long-double'):
                make("check")
        if '+quad' in spec:
            with working_dir('quad'):
                make("check")

    def install(self, spec, prefix):
        if '+double' in spec:
            with working_dir('double'):
                make("install")
        if '+float' in spec:
            with working_dir('float'):
                make("install")
        if '+long_double' in spec:
            with working_dir('long-double'):
                make("install")
        if '+quad' in spec:
            with working_dir('quad'):
                make("install")
