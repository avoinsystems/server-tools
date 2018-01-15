# -*- coding: utf-8 -*-
# © 2017 Avoin.Systems - Miku Laitinen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import models, fields, api
import ast


class IrFilters(models.Model):

    _inherit = 'ir.filters'

    @api.multi
    def _get_eval_domain(self):
        self.ensure_one()
        return ast.literal_eval(self.domain)

    is_dead_mans_switch_filter = fields.Boolean(
        "Is a Dead Man's Switch Filter",
        help="Checking this field will include this filter in the dead "
             "man's switch routine. If this filter returns any rows at "
             "any time, the dead man's switch will go off.",
    )
