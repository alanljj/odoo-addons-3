odoo.define('hr_timesheet_project_sheet.sheet', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var form_common = require('web.form_common');
var formats = require('web.formats');
var Model = require('web.DataModel');
var time = require('web.time');
var utils = require('web.utils');

var QWeb = core.qweb;
var _t = core._t;

var WeeklyTimesheet = form_common.FormWidget.extend(form_common.ReinitializeWidgetMixin, {
    events: {
        "click .oe_timesheet_weekly_account a": "go_to",
    },
    ignore_fields: function() {
        return ['line_id'];
    },
    init: function() {
        this._super.apply(this, arguments);
        this.set({
            sheets: [],
            date_from: false,
            date_to: false,
        });

        this.field_manager.on("field_changed:timesheet_ids", this, this.query_sheets);
        this.field_manager.on("field_changed:date_from", this, function() {
            this.set({"date_from": time.str_to_date(this.field_manager.get_field_value("date_from"))});
        });
        this.field_manager.on("field_changed:date_to", this, function() {
            this.set({"date_to": time.str_to_date(this.field_manager.get_field_value("date_to"))});
        });
        this.field_manager.on("field_changed:project_id", this, function() {
            this.set({"project_id": this.field_manager.get_field_value("project_id")});
        });
        this.on("change:sheets", this, this.update_sheets);
        this.res_o2m_drop = new utils.DropMisordered();
        this.render_drop = new utils.DropMisordered();
        this.description_line = _t("/");
    },
    go_to: function(event) {
        var id = JSON.parse($(event.target).data("id"));
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "res.users",
            res_id: id,
            views: [[false, 'form']],
        });
    },
    query_sheets: function() {
        if (this.updating) {
            return;
        }
        this.querying = true;
        var commands = this.field_manager.get_field_value("timesheet_ids");
        var self = this;
        this.res_o2m_drop.add(new Model(this.view.model).call("resolve_2many_commands", 
                ["timesheet_ids", commands, [], new data.CompoundContext()]))
            .done(function(result) {
                self.set({sheets: result});
                self.querying = false;
            });
    },
    update_sheets: function() {
        if(this.querying) {
            return;
        }
        this.updating = true;

        var commands = [form_common.commands.delete_all()];
        _.each(this.get("sheets"), function (_data) {
            var data = _.clone(_data);
            if(data.id) {
                commands.push(form_common.commands.link_to(data.id));
                commands.push(form_common.commands.update(data.id, data));
            } else {
                commands.push(form_common.commands.create(data));
            }
        });

        var self = this;
        this.field_manager.set_values({'timesheet_ids': commands}).done(function() {
            self.updating = false;
        });
    },
    initialize_field: function() {
        form_common.ReinitializeWidgetMixin.initialize_field.call(this);
        this.on("change:sheets", this, this.initialize_content);
        this.on("change:date_to", this, this.initialize_content);
        this.on("change:date_from", this, this.initialize_content);
        this.on("change:project_id", this, this.initialize_content);
    },
    initialize_content: function() {
        if(this.setting) {
            return;
        }

        // don't render anything until we have date_to and date_from
        if (!this.get("date_to") || !this.get("date_from")) {
            return;
        }

        // it's important to use those vars to avoid race conditions
        var dates;
        var employees;
        var timesheet_lines;
        var employee_names;
        var default_get;
        var self = this;
        return this.render_drop.add(new Model("account.analytic.line").call("default_get", [
            ['account_id','general_account_id','journal_id','date','name','user_id','product_id','product_uom_id','amount','unit_amount','project_id'],
            new data.CompoundContext({'project_id': self.get('project_id')})
        ]).then(function(result) {
            default_get = result;
            // calculating dates
            dates = [];
            var start = self.get("date_from");
            var end = self.get("date_to");
            while (start <= end) {
                dates.push(start);
                var m_start = moment(start).add(1, 'days');
                start = m_start.toDate();
            }
            timesheet_lines = _(self.get('sheets')).chain()
	            .map(function(el) {
	                // much simpler to use only the id in all cases
	            	if (typeof(el.user_id) === "object") 
	                    el.user_id = el.user_id[0];
	                return el;
	            }).value();
            
            // group by employee
            employees = _.groupBy(timesheet_lines, function(el) {
                return el.user_id;
            });

            employees = _(employees).chain().map(function(lines, user_id) {
            	var user_id = lines[0].user_id;
            	var employees_defaults = _.extend({}, default_get, (employees[user_id] || {}).value || {});
                // group by days
                user_id = (user_id === "false")? false : Number(user_id);
                var index = _.groupBy(lines, "date");
                var days = _.map(dates, function(date) {
                    var day = {day: date, lines: index[time.date_to_str(date)] || []};
                    // add line where we will insert/remove hours
                    var to_add = _.find(day.lines, function(line) { return line.name === self.description_line; });
                    if (to_add) {
                        day.lines = _.without(day.lines, to_add);
                        day.lines.unshift(to_add);
                    } else {
                        day.lines.unshift(_.extend(_.clone(employees_defaults), {
                            name: self.description_line,
                            unit_amount: 0,
                            date: time.date_to_str(date),
                            user_id: user_id,
                        }));
                    }
                    return day;
                });
                
                var partner_id = undefined;

                if(lines[0].partner_id){
                    if(parseInt(lines[0].partner_id, 10) == lines[0].partner_id){
                        partner_id = lines[0].partner_id;
                    } else {
                        partner_id = lines[0].partner_id[0];
                    }
                }
                
                return {user_id: user_id, days: days, employees_defaults: employees_defaults, partner_id: partner_id};
            }).value();
            
            // we need the name_get of the employee
            return new Model("res.users").call("name_get", [_.pluck(employees, "user_id"),
                new data.CompoundContext()]).then(function(result) {
                employee_names = {};
                _.each(result, function(el) {
                	employee_names[el[0]] = el[1];
                });
                employees = _.sortBy(employees, function(el) {
                    return employee_names[el.user_id];
                });
            });
            
        })).then(function(result) {
            // we put all the gathered data in self, then we render
            self.dates = dates;
            self.employees = employees;
            self.employee_names = employee_names;
            self.default_get = default_get;
            //real rendering
            self.display_data();
        });
    },
    display_data: function() {
        var self = this;
        self.$el.html(QWeb.render("hr_timesheet_project_sheet.WeeklyTimesheet", {widget: self}));
        _.each(self.employees, function(employee) {
            _.each(_.range(employee.days.length), function(day_count) {
                self.get_box(employee, day_count).html(self.sum_box(employee, day_count, true));
            });
        });
        
        self.display_totals();
    },
    get_box: function(employee, day_count) {
    	return this.$('[data-employee="' + employee.user_id + '"][data-day-count="' + day_count + '"]');
    },
    sum_box: function(employee, day_count, show_value_in_hour) {
        var line_total = 0;
        _.each(employee.days[day_count].lines, function(line) {
            line_total += line.unit_amount;
        });
        return (show_value_in_hour && line_total !== 0)?this.format_client(line_total):line_total;
    },
    display_totals: function() {
        var self = this;
        var day_tots = _.map(_.range(self.dates.length), function() { return 0; });
        var super_tot = 0;
        _.each(self.employees, function(employee) {
            var acc_tot = 0;
            _.each(_.range(self.dates.length), function(day_count) {
                var sum = self.sum_box(employee, day_count);
                acc_tot += sum;
                day_tots[day_count] += sum;
                super_tot += sum;
            });
            self.$('[data-employee-total="' + employee.user_id + '"]').html(self.format_client(acc_tot));
        });
        _.each(_.range(self.dates.length), function(day_count) {
            self.$('[data-day-total="' + day_count + '"]').html(self.format_client(day_tots[day_count]));
        });
        this.$('.oe_timesheet_weekly_supertotal').html(self.format_client(super_tot));
    },
    //converts float value to hour
    format_client:function(value){
        return formats.format_value(value, { type:"float_time" });
    },
});

core.form_custom_registry.add('weekly_timesheet', WeeklyTimesheet);

});
