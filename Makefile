all:
	pyuic5 urxui/mainwindow_ui.ui -o urxui/mainwindow_ui.py
	#pyrcc5 urxui/resources.qrc -o urxui/resources.py
run:
	PYTHONPATH=$(shell pwd)
	python3 app.py
edit:
	qtcreator urxui/mainwindow_ui.ui
