from pip.req import parse_requirements
from pip.download import PipSession

install_reqs = parse_requirements('requirements.txt', session=PipSession())
reqs = [str(ir.req) for ir in install_reqs]

from setuptools import setup

setup(name='myrabbit_py',
      version='0.0.1',
      description='',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
      ],
      url='https://github.com/bsab/MyRabbit2.git',
      author='Sabatino Severino',
      author_email='sab.severino01@gmail.com',
      license='MIT',
      packages=['myrabbit_py'],
      install_requires=reqs,
      test_suite='nose.collector',
      tests_require=[
          'nose'
      ],
      zip_safe=False)
