import setuptools

setup_params = dict(
    name='designate-ruiner',
    version='0.0.1',
    entry_points={
        'console_scripts': [
            'ruiner=ruiner.common.runner:main',
        ],
    },
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
