from setuptools import setup

setup(name='myrabbit',
      version='0.0.1',
      description='',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
      ],
      url='http://github.com/....',
      author='Sabatino Severino',
      author_email='git@stibbsy.co.uk',
      license='MIT',
      packages=['myrabbit'],
      install_requires=[
            'requests'
      ],
      test_suite='nose.collector',
      tests_require=[
          'nose'
      ],
      zip_safe=False)
