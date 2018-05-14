#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, GdkPixbuf, Gdk, Gio, GObject,GLib



import signal
import os
import subprocess
import json
import sys
import syslog
import time
import threading
import tempfile
from shutil import copyfile

from edupals.ui.n4dgtklogin import *
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


from . import settings
import gettext
#gettext.textdomain(settings.TEXT_DOMAIN)
_ = gettext.gettext

class MainWindow:
	
	def __init__(self):

		self.core=Core.Core.get_core()
		self.config_dir=os.path.expanduser("/etc/bellScheduler/")
		self.holiday_token=self.config_dir+"enabled_holiday_token"


	#def init

	
	def load_gui(self):
		
		gettext.textdomain(settings.TEXT_DOMAIN)
		builder=Gtk.Builder()
		builder.set_translation_domain(settings.TEXT_DOMAIN)
		ui_path=self.core.ui_path
		builder.add_from_file(ui_path)

		self.css_file=self.core.rsrc_dir+"bell-scheduler.css"
				
		self.stack_window= Gtk.Stack()
		self.stack_window.set_transition_duration(750)
		self.stack_window.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
		self.stack_window.set_margin_top(0)
		self.stack_window.set_margin_bottom(0)
		
		self.main_window=builder.get_object("main_window")
		self.main_window.set_title("Bell Scheduler")
		self.main_box=builder.get_object("main_box")
		self.login=N4dGtkLogin()
		self.login.set_allowed_groups(['adm','teachers'])
		self.login.hide_server_entry()
		desc=_("Welcome to the Bell Scheduler.\nFrom here you can program multiple alarms for entry, exit, recess or any other event")
		self.login.set_info_text("<span foreground='black'>Bell Scheduler</span>",_("Bell Scheduler"),"<span foreground='black'>"+desc+"</span>\n")
		image=os.path.join(self.core.rsrc_dir,"bell.png")
		self.login.set_info_background(image=image,cover=True)
		self.login.after_validation_goto(self._signin)

		self.option_box=builder.get_object("options_box")
		self.add_button=builder.get_object("add_button")
		self.export_button=builder.get_object("export_button")
		self.import_button=builder.get_object("import_button")
		self.manage_holiday_button=builder.get_object("manage_holiday_button")
		self.enable_holiday_label=builder.get_object("enable_holiday_label")
		self.enable_holiday_switch=builder.get_object("enable_holiday_switch")
		self.search_entry=builder.get_object("search_entry")
		self.msg_label=builder.get_object("msg_label")
		self.save_button=builder.get_object("save_button")
		self.cancel_button=builder.get_object("cancel_button")
		self.return_button=builder.get_object("return_button")

		self.waiting_window=builder.get_object("waiting_window")
		self.waiting_label=builder.get_object("waiting_plabel")
		self.waiting_pbar=builder.get_object("waiting_pbar")
		self.waiting_window.set_transient_for(self.main_window)

		self.bellBox=self.core.bellBox
		self.editBox=self.core.editBox
		self.holidayBox=self.core.holidayBox

		self.stack_window.add_titled(self.login, "login", "Login")
		self.stack_window.add_titled(self.option_box,"optionBox", "Option Box")
		self.stack_window.show_all()
		self.main_box.pack_start(self.stack_window,True,True,0)

		self.stack_opt= Gtk.Stack()
		self.stack_opt.set_transition_duration(750)
		self.stack_opt.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)

		
		self.stack_opt.add_titled(self.bellBox,"bellBox", "Bell Box")
		self.stack_opt.add_titled(self.editBox,"editBox", "Edit Box")
		self.stack_opt.add_titled(self.holidayBox,"holidayBox", "Holiday Box")

		
		self.stack_opt.show_all()

		self.option_box.pack_start(self.stack_opt,True,True,5)
		
		self.set_css_info()
		self.init_threads()
		self.connect_signals()
		self.manage_menubar(True,True)
		self.manage_down_buttons(False)
		self.cont=0
		self.main_window.show()
		self.stack_window.set_transition_type(Gtk.StackTransitionType.NONE)
		self.stack_window.set_visible_child_name("login")
		self.return_button.hide()
		#self.holiday_control=False

		
	#def load_gui


	def init_threads(self):

		self.export_bells_t=threading.Thread(target=self.export_bells)
		self.import_bells_t=threading.Thread(target=self.import_bells)
		self.recovery_bells_t=threading.Thread(target=self.recovery_bells)
		self.enable_holiday_control_t=threading.Thread(target=self.enable_holiday_control)

		self.export_bells_t.daemon=True
		self.import_bells_t.daemon=True
		self.recovery_bells_t.daemon=True
		self.enable_holiday_control_t.daemon=True

		self.export_bells_t.launched=False
		self.import_bells_t.launched=False
		self.recovery_bells_t.launched=False
		self.enable_holiday_control_t.launched=False

		GObject.threads_init()

	#def init_threads	

	def set_css_info(self):
		
		
		self.style_provider=Gtk.CssProvider()
		f=Gio.File.new_for_path(self.css_file)
		self.style_provider.load_from_file(f)
		Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),self.style_provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
		self.main_window.set_name("WINDOW")
		self.waiting_label.set_name("WAITING_LABEL")

		#self.banner_box.set_name("BANNER_BOX")

	#def set_css_info	
				
			
	def connect_signals(self):
		
		self.main_window.connect("destroy",self.quit)
		self.add_button.connect("clicked",self.add_bell)
		self.save_button.connect("clicked",self.core.editBox.gather_values)
		self.cancel_button.connect("clicked",self.cancel_clicked)
		self.export_button.connect("clicked",self.export_clicked)
		self.import_button.connect("clicked",self.import_clicked)
		self.search_entry.connect("changed",self.search_entry_changed)
		self.manage_holiday_button.connect("clicked",self.manage_holiday_button_clicked)
		self.return_button.connect("clicked",self.return_button_clicked)
		self.enable_holiday_switch.connect("notify::active",self.enable_holiday_switch_clicked)

	#def connect_signals	

				
	def _signin(self,user,pwd,server):

		self.core.bellmanager.credentials=[user,pwd]
		self.core.holidayBox.credentials=[user,pwd]
		self._init_holiday_switch()
		self.manage_down_buttons(False)
		result_sync=self.core.bellmanager.sync_with_cron()
		if result_sync["status"]:
			self.load_info()
			self.core.bellBox.draw_bell(False)
		else:
			self.manage_menubar(False)
			self.manage_message(True,result_sync["code"])

		self.stack_window.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
		self.stack_window.set_visible_child_name("optionBox")
		#self.stack_opt.set_visible_child_name("bellBox")


	#def _signin

	def _init_holiday_switch(self):

		self.holiday_control=False

		if os.path.exists(self.holiday_token):
			self.enable_holiday_switch.set_active(True)
		else:
			self.enable_holiday_switch.set_active(False)

	#def _init_holiday_switch
	

	def load_info(self):
	
		self.read_conf=self.core.bellmanager.read_conf()
		self.bells_info=self.core.bellmanager.bells_config.copy()
		self.order_bells=self.core.bellmanager.get_order_bell()	
		if not self.read_conf['status']:
			if self.cont==0:
				self.manage_message(True,self.read_conf['code'])
				self.manage_menubar(False,False)	
		else:
			self.manage_menubar(True)			
	
	#def load_info	

	def add_bell(self,widget):

		self.manage_menubar(False)
		self.manage_down_buttons(True)
		self.core.editBox.init_form()
		self.core.editBox.render_form()
		self.stack_opt.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
		self.stack_opt.set_visible_child_name("editBox")

	#def add_bell	


	def cancel_clicked(self,widget):

		self.manage_menubar(True)
		self.manage_down_buttons(False)
		self.core.editBox.remove(self.core.editBox.main_box)
		self.stack_opt.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
		self.stack_opt.set_visible_child_name("bellBox")
		
	#def cancel_clicked	

	def export_clicked(self,widget):

		dialog = Gtk.FileChooserDialog(_("Please choose a file to save bells list"), None,
		Gtk.FileChooserAction.SAVE,(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
		Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
		dialog.set_do_overwrite_confirmation(True)
		response = dialog.run()
		
		if response == Gtk.ResponseType.OK:
			self.dest=dialog.get_filename()
			dialog.destroy()
			self.waiting_label.set_text(self.get_msg(26))			
			self.waiting_window.show_all()
			self.init_threads()
			self.export_bells_t.start()
			GLib.timeout_add(100,self.pulsate_export_bells)
		dialog.destroy()	

	#def export_clicked	

	def pulsate_export_bells(self):

		if self.export_bells_t.is_alive():
			self.waiting_pbar.pulse()
			return True

		else:
			self.waiting_window.hide()
			if self.export_result['status']:
				self.manage_message(False,self.export_result['code'])
			else:
				self.manage_message(True,self.export_result['code'])

		return False

	#def pulsate_export_bell	

	def export_bells(self):

		self.export_result=self.core.bellmanager.export_bells_conf(self.dest)				
	
	#def export_bells

	def import_clicked(self,widget):

		self.loading_errors=False
		self.backup=True

		dialog = Gtk.MessageDialog(None,0,Gtk.MessageType.WARNING, Gtk.ButtonsType.YES_NO, "BELL SCHEDULER")
		dialog.format_secondary_text(_("New bells configuration will be loaded and replace the existing configutarion. Do you want to continue?"))
		response=dialog.run()
		dialog.destroy()
		if response == Gtk.ResponseType.YES:
			dialog = Gtk.FileChooserDialog(_("Please choose a file to load bells list"), None,
			Gtk.FileChooserAction.OPEN,(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
			self.add_filter(dialog)
			response = dialog.run()
			if response == Gtk.ResponseType.OK:
				self.orig=dialog.get_filename()
				dialog.destroy()
				self.waiting_label.set_text(self.get_msg(27))			
				self.waiting_window.show_all()
				self.init_threads()
				self.import_bells_t.start()
				GLib.timeout_add(100,self.pulsate_import_bells)

		dialog.destroy()
				
	#def import_clicked

	def add_filter(self,dialog):
		
		filter_zip = Gtk.FileFilter()
		filter_zip.set_name("Zip files")
		filter_zip.add_mime_type("application/zip")
		dialog.add_filter(filter_zip)

	#def add_filter	

	def pulsate_import_bells(self):

		if self.import_bells_t.is_alive():
			self.waiting_pbar.pulse()
			return True

		else:
			self._init_holiday_switch()
			self.waiting_window.hide()
			if self.import_result['status']:
				self.load_info()
				if self.read_conf['status']:
					try:
						self.core.bellBox.draw_bell(False)
						if not self.loading_errors:
							self.manage_message(False,self.import_result['code'])
						else:
							self.manage_message(True,13)	
					except:
						self.backup=False
						self.orig=self.import_result['data']+".zip"
						self.init_threads()
						self.recovery_bells_t.start()
						self.waiting_label.set_text(self.get_msg(28))
						GLib.timeout_add(100,self.pulsate_recovery_bells)
						return False	
				else:
					self.manage_message(True,self.read_conf['code'])	
					self.cont=0
					return False

			else:
				self.manage_message(True,self.import_result['code'])	
				self.cont=0
				return False

	#def pulsate_import_bells

	def import_bells(self):

		self.import_result=self.core.bellmanager.import_bells_conf(self.orig,self.backup)

	#def import_bells		


	def pulsate_recovery_bells(self):

		if self.recovery_bells_t.is_alive():
			self.waiting_pbar.pulse()
			return True

		else:
			self.waiting_window.hide()
			self.load_info()
			try:
				self.core.bellBox.draw_bell(False)
				if not self.loading_errors:
					self.manage_message(True,9)
				else:
					self.manage_message(True,9)	
			except:
				self.manage_message(True,self.recovery_result['code'])	
				return False	

		return False
	
	#def pulsate_recovery_bells		
	
	
	def recovery_bells(self):

		self.recovery_result=self.core.bellmanager.recovery_bells_conf(self.orig,self.backup)		

	#def recovery_bells

	def search_entry_changed(self,widget):

		self.core.bellBox.init_bell_list() 
		self.load_info()
		self.search_list=self.bells_info.copy()

		search=self.search_entry.get_text().lower()
		if search=="":
			self.core.bellBox.draw_bell(False)
		else:
			for item in self.bells_info:
				time=self.core.bellmanager.format_time(item)
				hour=str(time[0])
				minute=str(time[1])
				cron=str(time[2])
				name=self.bells_info[item]["name"].lower()
				days=[]
				if self.bells_info[item]["weekdays"]["0"]:
					days.append(_("Monday"))
					days.append(_("M"))
					days.append(_("Mon"))
				if self.bells_info[item]["weekdays"]["1"]:
					days.append(_("Tuesday"))
					days.append(_("T"))
					days.append(_("Tue"))
				if self.bells_info[item]["weekdays"]["2"]:
					days.append(_("Wednesday"))	
					days.append(_("W"))
					days.append(_("Wed"))
				if self.bells_info[item]["weekdays"]["3"]:
					days.append(_("Thursday"))
					days.append(_("R"))
					days.append(_("Thu"))
				if self.bells_info[item]["weekdays"]["4"]:
					days.append(_("Friday"))
					days.append(_("F"))	
					days.append(_("Fri"))

				
				if search in hour or search in minute or search in name or search in cron or search in [ x.lower() for x in days]:
					pass
				else:
					self.search_list.pop(item)

			if len(self.search_list)>0:
					self.search_order=self.core.bellmanager.get_order_bell(self.search_list)		
					self.core.bellBox.draw_bell(True)
			
	#def search_entry_changed				

	def manage_menubar(self,active,hide=None):
	
		if hide:
			self.add_button.hide()
			self.import_button.hide()
			self.export_button.hide()
			self.search_entry.hide()
		else:
			self.add_button.show()
			self.import_button.show()
			self.export_button.show()
			self.search_entry.show()

		if active:
			self.add_button.set_sensitive(True)
			self.import_button.set_sensitive(True)
			self.export_button.set_sensitive(True)
			self.search_entry.set_sensitive(True)
			self.manage_holiday_button.set_sensitive(True)
			self.enable_holiday_switch.set_sensitive(True)
		else:
			self.add_button.set_sensitive(False)
			self.import_button.set_sensitive(False)
			self.export_button.set_sensitive(False)
			self.search_entry.set_sensitive(False)
			self.manage_holiday_button.set_sensitive(False)
			self.enable_holiday_switch.set_sensitive(False)

	#def manage_menubar		

	
	def manage_down_buttons(self,show):
	
		if show:
			self.cancel_button.show()
			self.save_button.show()
			self.msg_label.hide()
			self.enable_holiday_switch.hide()
			self.enable_holiday_label.hide()
		else:
			self.cancel_button.hide()
			self.save_button.hide()
			self.msg_label.hide()
			self.enable_holiday_switch.show()
			self.enable_holiday_label.show()


	#def manage_down_buttons					

			
	def manage_message(self,error,code):

		msg=self.get_msg(code)
		
		if error:
			self.msg_label.set_name("MSG_ERROR_LABEL")
		else:
			self.msg_label.set_name("MSG_CORRECT_LABEL")	

		self.msg_label.set_text(msg)
		self.msg_label.show()

	#def manage_message		


	def get_msg(self,code):

		if 	code==1:
			msg_text=_("You must indicate a name for the alarm")
		elif code==2:
			msg_text=_("Sound file is not correct")
		elif code==3:
			msg_text=_("You must indicate sound file")
		elif code==4:
			msg_text=_("Image file is not correct")
		elif code==5:
			msg_text=_("You must indicate a image file")
		elif code==6:
			msg_text=_("You must indicate a url")
		elif code==7:
			msg_text=_("You must indicate a directory")	
		elif code==8:
			msg_text=_("The sound file or url indicated is not reproducible")
		elif code==9:
			msg_text=_("File has errors. Unabled to load it")
		elif code==10:
			msg_text=_("File loaded succesfully")
		elif code==11:
			msg_text=_("File saved succcesfully")
		elif code==12:
			msg_text=_("Unable to save file")	
		elif code==13:
			msg_text=_("File loaded with errors")	
		elif code==14:
			msg_text=_("Bell deleted successfully")	
		elif code==15:
			msg_text=_("Bell edited successfully")
		elif code==16:
			msg_text=_("Bell activated successfully")
		elif code==17:
			msg_text=_("Bell deactivated successfully")
		elif code==18:
			msg_text=_("Bell created successfully")		
		elif code==19:
			msg_text=_("Unabled to edit the Bell due to problems with cron sync")	
		elif code==20:
			msg_text=_("Unabled to create the Bell due to problems with cron sync")
		elif code==21:
			msg_text=_("Unabled to delete the Bell due to problems with cron sync")	
		elif code==22:
			msg_text=_("Unabled to activate the Bell due to problems with cron sync")	
		elif code==23:
			msg_text=_("Unabled to deactivate the Bell due to problems with cron sync")	
		elif code==24:
			msg_text=_("Unabled to copy image and/or sound file to work directory")	
		elif code==25:
			msg_text=_("Unabled to read bells configuration file")	
		elif code==26:
			msg_text=_("Exporting bells configuration. Wait a moment...")	
		elif code==27:
			msg_text=_("Importing bells configuration. Wait a moment...")
		elif code==28:
			msg_text=_("Revovering previous bells configuration. Wait a moment...")	
		elif code==29:
			msg_text=_("ERROR: File or directory not available")
		elif code==30:
			msg_text=_("Validating the data entered...")		
		elif code==31:
			msg_text=_("Detected alarms with errors")
		elif code==32:
			msg_text=_("Activating holiday control.Wait a moment...")
		elif code==33:
			msg_text=_("Deactivating holiday control.Wait a moment...")
		elif code==34:
			msg_text=_("Holiday control deactivated successfully")
		elif code==35:
			msg_text=_("Holiday control activated successfully")
		elif code==36:
			msg_text=_("Unabled to apply changes due to problems with cron sync")
		elif code==37:
			msg_text=_("Unabled to load bell list due to problems with cron sync")	

			
		return msg_text

	#def get_msg	
			
	def manage_holiday_button_clicked(self,widget):

		self.core.holidayBox.start_api_connect()
		self.msg_label.hide()
		self.manage_menubar(False)
		self.enable_holiday_switch.hide()
		self.enable_holiday_label.hide()
		self.stack_opt.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
		self.stack_opt.set_visible_child_name("holidayBox")
		self.return_button.show()

	#def manage_holiday_button_clicked	

	def return_button_clicked(self,widget):

		gettext.textdomain(settings.TEXT_DOMAIN)
		self.manage_menubar(True)
		self.stack_opt.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
		self.stack_opt.set_visible_child_name("bellBox")
		self.return_button.hide()
		self.enable_holiday_switch.show()
		self.enable_holiday_label.show()



	#def return_button_clicked

	def enable_holiday_switch_clicked(self,switch,gparam):

		if switch.get_active():
			if not os.path.exists(self.holiday_token):
				self.holiday_control=True
				self.holiday_action="enable"

		else:
			if os.path.exists(self.holiday_token):
				self.holiday_control=True
				self.holiday_action="disable"

		if self.holiday_control:
			self.waiting_label.set_text(self.get_msg(32))			
			self.waiting_window.show_all()
			self.init_threads()
			self.enable_holiday_control_t.start()
			GLib.timeout_add(100,self.pulsate_enable_holiday_control)


	#def enable_holiday_switch_clicked

	def pulsate_enable_holiday_control(self):


		if self.enable_holiday_control_t.is_alive():
			self.waiting_pbar.pulse()
			return True

		else:
			self.waiting_window.hide()
			if self.enable_holiday_result['status']:
				self.manage_message(False,self.enable_holiday_result['code'])
			else:
				self.manage_message(True,self.enable_holiday_result['code'])

		return False

	#def pulsate_enable_holiday_control	

	def enable_holiday_control(self):

		self.enable_holiday_result=self.core.bellmanager.enable_holiday_control(self.holiday_action)		
	
	#def enable_holiday_control


	def quit(self,widget):

		Gtk.main_quit()	

	#def quit	

	def start_gui(self):
		
		GObject.threads_init()
		Gtk.main()
		
	#def start_gui


	
#class MainWindow

from . import Core
