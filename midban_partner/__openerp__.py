# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@pexego.es>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Midban Partner",
    "version": "1.0",
    "author": "Pexego",
    "category": "Custom",
    "website": "www.pexego.es",
    "description": """
    This module add custom fields an behavior for MIDBAN partners.

    Creates a statusbar in Clients and Suplliers with the following states:
        Validate pending
        Logistic validation pending
        Comercial validation pending
        Validated
        Registered
        Unregistered

    When you create a Supplier/client is desactived by defaut until state
    change to register.
    You can see the partners in registering process or unregistered partners
    using filters.

    This module adds a history in clients/Supliers that record states changes
    and changes dates.

    Also adds a model of suppliers service days that you can select on
    suplliers view in a many2many relation.

    Provides a model of unregister reasons selected when you unregister a
    partner. Provides a wizard to do that.

    New model for supplier transports.

    The configuration of new models can be seen in configuration menu of
    sales and purchases.
    """,
    "images": [],
    "depends": ["base",
                # "account_report_company",
                "mail",
                "email_template",
                "stock",
                "purchase",
                # "report_aeroo"
                ],
    "data": ['wizard/process_unregister_partner_view.xml',
             "partner_data.xml",
             "partner_view.xml",
             # "partner_report.xml",
             "partner_workflow.xml",
             'security/ir.model.access.csv',
             'wizard/process_unregister_partner_view.xml'],
    "demo": [],
    "test": [],
    "installable": True,
    "application": True,
}
