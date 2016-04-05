from distutils.core import setup
from distutils.command.install_data import install_data


setup(name="urxui", 
      version="0.0.2",
      description="Minimal UI to urx Python library",
      author="Olivier Roulet-Dubonnet",
      author_email="olivier.roulet@gmail.com",
      url='https://github.com/oroulet/urxui',
      packages=["urxui"],
      provides=["urxui"],
      license="GNU General Public License v3",

      install_requires=["urx"],
      entry_points={'console_scripts':
                    ['urxui = urxyu.mainwindow:main']
                    },
      classifiers=[
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Operating System :: OS Independent",
            "Topic :: System :: Hardware :: Hardware Drivers",
            "Topic :: Software Development :: Libraries :: Python Modules",
      ]
      )


