#coding: utf-8
## Copyright 2008-2011 Luc Saffre
## This file is part of the Lino project.
## Lino is free software; you can redistribute it and/or modify 
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
## Lino is distributed in the hope that it will be useful, 
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
## GNU General Public License for more details.
## You should have received a copy of the GNU General Public License
## along with Lino; if not, see <http://www.gnu.org/licenses/>.


from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

#~ from south.modelsinspector import add_introspection_rules
#~ add_introspection_rules([], ["^lino\.fields\.LanguageField"])
#~ add_introspection_rules([], ["^lino\.fields\.PriceField"])
#~ add_introspection_rules([], ["^lino\.fields\.KnowledgeField"])
#~ add_introspection_rules([], ["^lino\.fields\.StrengthField"])
#~ add_introspection_rules([], ["^lino\.fields\.PercentageField"])
#~ add_introspection_rules([], ["^lino\.fields\.MyDateField"])
#~ add_introspection_rules([], ["^lino\.fields\.MonthField"])
#~ add_introspection_rules([], ["^lino\.fields\.QuantityField"])
#~ add_introspection_rules([], ["^lino\.fields\.HtmlTextField"])

from lino.utils import choosers

LANGUAGE_CHOICES = [ (k,_(v)) for k,v in settings.LANGUAGES ]

class LanguageField(models.CharField):
    def __init__(self, *args, **kw):
        defaults = dict(
            verbose_name=_("Language"),
            choices=LANGUAGE_CHOICES,
            max_length=2,
            )
        defaults.update(kw)
        models.CharField.__init__(self,*args, **defaults)

    
#~ TEXT_FORMAT_PLAIN = 'plain'
#~ TEXT_FORMAT_HTML = 'html'
#~ TEXT_FORMAT_TINYMCE = 'tinymce'
#~ TEXT_FORMAT_VINYLFOX = 'vinylfox'
    

class RichTextField(models.TextField):
    """
    Only difference with Django's `models.TextField` is that you can 
    specify a keyword argument `format` to 
    override the global :attr:`lino.Lino.textfield_format`.
    """
    def __init__(self,*args,**kw):
        self.textfield_format = kw.pop('format',None)
        models.TextField.__init__(self,*args,**kw)
        
    def set_format(self,fmt):
        self.textfield_format = fmt
    
  
class PercentageField(models.SmallIntegerField):
    def __init__(self, *args, **kw):
        defaults = dict(
            max_length=3,
            )
        defaults.update(kw)
        models.SmallIntegerField.__init__(self,*args, **defaults)
  
#~ class MonthField(models.CharField):
class MonthField(models.DateField):
    def __init__(self, *args, **kw):
        #~ defaults = dict(
            #~ max_length=10,
            #~ )
        #~ defaults.update(kw)
        #~ models.CharField.__init__(self,*args, **defaults)
        models.DateField.__init__(self,*args, **kw)
  
class PriceField(models.DecimalField):
    def __init__(self, *args, **kwargs):
        defaults = dict(
            max_length=10,
            max_digits=10,
            decimal_places=2,
            )
        defaults.update(kwargs)
        super(PriceField, self).__init__(*args, **defaults)
        
    def formfield(self, **kwargs):
        fld = super(PriceField, self).formfield(**kwargs)
        # display size is smaller than full size:
        fld.widget.attrs['size'] = "6"
        fld.widget.attrs['style'] = "text-align:right;"
        return fld
        
class MyDateField(models.DateField):
        
    def formfield(self, **kwargs):
        fld = super(MyDateField, self).formfield(**kwargs)
        # display size is smaller than full size:
        fld.widget.attrs['size'] = "8"
        return fld
        
        
        
class QuantityField(models.DecimalField):
    def __init__(self, *args, **kwargs):
        defaults = dict(
            max_length=5,
            max_digits=5,
            decimal_places=0,
            )
        defaults.update(kwargs)
        super(QuantityField, self).__init__(*args, **defaults)
        
    def formfield(self, **kwargs):
        fld = super(QuantityField, self).formfield(**kwargs)
        fld.widget.attrs['size'] = "3"
        fld.widget.attrs['style'] = "text-align:right;"
        return fld
        
class DisplayField:
    editable = False
    choices = None
    blank = True
    drop_zone = None
    #~ bbar = None
    def __init__(self,verbose_name=None,**kw):
        self.verbose_name = verbose_name
        for k,v in kw.items():
            assert hasattr(self,k)
            setattr(self,k,v)
        
class HtmlBox(DisplayField):
    pass
    
#~ class QuickAction(DisplayField):
    #~ pass
    
#~ from django.db.models.fields import Field

class VirtualField: # (Field):
    """
    Currently implemented only by :class:`lino.utils.mti.EnableChild`.    
    """
    editable = False
    
    def __init__(self,return_type,get):
        self.return_type = return_type # a Django Field instance
        self.get = get
        #~ self.set = set
        #~ self.name = None
        #~ Field.__init__(self)
        for k in ('to_python choices save_form_data value_to_string'.split()):
        #~ for k in ('get_internal_type','to_python'):
            setattr(self,k,getattr(return_type,k))
            
    def set_value_in_object(self,obj,value,request=None):
        """
        Stores the specified `value` in the specified model instance `obj`.
        
        Note that any implementation must also return `obj`,
        and callers must be ready to get another instance.
        This special behaviour is needed to implement 
        :class:`lino.utils.mti.EnableChild`.
        """
        raise NotImplementedError
        
    def lino_kernel_setup(self,model,name):
        self.model = model
        self.name = name
        self.return_type.name = name
        self.return_type.attname = name
        
    #~ def contribute_to_class(self, cls, name):
        #~ "Called from lino.core.kernel.setup"
        #~ self.name = name
        #~ self.model = cls
        
    #~ def get_db_prep_save(self, value, connection):
        #~ raise NotImplementedError
    #~ def pre_save(self, model_instance, add):
        #~ raise NotImplementedError
        
    def value_from_object(self,request,obj):
        """
        Return the value of this field in the specified model instance `obj`.
        `request` may be `None`, it's forwarded to the getter method who may 
        decide to return values depending on it.
        """
        m = self.get
        #~ assert m.func_code.co_argcount == 2, (self.name, m.func_code.co_varnames)
        #~ print self.field.name
        return m(obj,request)
        
    
class GenericForeignKeyIdField(models.PositiveIntegerField):
    """"""
    def __init__(self, type_field, *args, **kw):
        self.type_field = type_field
        models.PositiveIntegerField.__init__(self,*args, **kw)
    
    pass
    