[1mdiff --git a/midban_depot_stock/wizard/assign_task_wzd.py b/midban_depot_stock/wizard/assign_task_wzd.py[m
[1mindex cfbae27..355577d 100644[m
[1m--- a/midban_depot_stock/wizard/assign_task_wzd.py[m
[1m+++ b/midban_depot_stock/wizard/assign_task_wzd.py[m
[36m@@ -624,7 +624,6 @@[m [mclass assign_task_wzd(osv.TransientModel):[m
         if context is None:[m
             context = {}[m
         move_obj = self.pool.get('stock.move')[m
[31m-[m
         res = [][m
         obj = self.browse(cr, uid, ids[0], context=context)[m
         selected_route = obj.trans_route_id and obj.trans_route_id.id or False[m
[36m@@ -647,15 +646,6 @@[m [mclass assign_task_wzd(osv.TransientModel):[m
             ('picking_id.min_date', '>=', start_date),[m
             ('picking_id.min_date', '<=', end_date),[m
         ][m
[31m-        domain1 = [[m
[31m-            ('picking_type_id', '=', obj.warehouse_id.pick_type_id.id),[m
[31m-            ('|'),('product_id.picking_location_id','=', False),('product_id.picking_location_id', 'child_of', loc_ids),[m
[31m-            ('state', 'in', ['confirmed', 'assigned']),[m
[31m-            ('picking_id.operator_id', '=', False),[m
[31m-            ('picking_id.trans_route_id', '=', selected_route),[m
[31m-            ('picking_id.min_date', '>=', start_date),[m
[31m-            ('picking_id.min_date', '<=', end_date),[m
[31m-        ][m
         res = move_obj.search(cr, uid, domain, context=context)[m
         print res[m
         return (res, selected_route)[m
[36m@@ -665,8 +655,6 @@[m [mclass assign_task_wzd(osv.TransientModel):[m
         For all moves from a same product, get the new pickings, or the[m
         original picking if it only have one move.[m
         """[m
[31m-[m
[31m-        #import ipdb; ipdb.set_trace()[m
         res = set()[m
         if context is None:[m
             context = {}[m
[1mdiff --git a/midban_depot_stock/wizard/create_camera_locations.py b/midban_depot_stock/wizard/create_camera_locations.py[m
[1mindex 7d6ea51..262b2b8 100644[m
[1m--- a/midban_depot_stock/wizard/create_camera_locations.py[m
[1m+++ b/midban_depot_stock/wizard/create_camera_locations.py[m
[36m@@ -111,7 +111,6 @@[m [mclass create_camera_locations(models.TransientModel):[m
         bcd_code = item.camera_prefix + item.code_row[m
         bcd_name = item.camera_prefix + " " + item.code_row[m
         # Create Picking vals[m
[31m-        #import ipdb; ipdb.set_trace()[m
         for name in pick_names:[m
             if len(name.split('/'))==2:[m
                 fila = name.split('/')[0][m
[1mdiff --git a/midban_depot_stock/wizard/manual_transfer_wzd.py b/midban_depot_stock/wizard/manual_transfer_wzd.py[m
[1mindex 029a41a..af5c504 100644[m
[1m--- a/midban_depot_stock/wizard/manual_transfer_wzd.py[m
[1m+++ b/midban_depot_stock/wizard/manual_transfer_wzd.py[m
[36m@@ -250,7 +250,6 @@[m [mclass transfer_lines(models.TransientModel):[m
         line = self[0]  # Is called always line by line[m
 [m
         #op_vals = line.get_operation_vals(pick_obj)[m
[31m-        #import ipdb; ipdb.set_trace()[m
         # Operation to move products without pack or from a pack[m
         if line.product_id:[m
             qty = line.quantity[m
