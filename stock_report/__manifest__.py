# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Stock Move Reports',
    'sequence': 1,
    'author': 'Mohamed Yaseen Dahab',
    'category': 'Accounting/Accounting',
    'summary': '',
    'description': """



    """,
    'version': '1.0',
    'depends': ['base', 'stock', 'account', 'sale', 'purchase'],
    'data': [
        'views/inherit_stock_valuation.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
