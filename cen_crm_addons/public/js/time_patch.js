console.log("Time Patch: Initializing ControlTime UI Overrides...");

function init_time_patch() {
    if (typeof frappe === "undefined" || !frappe.ui || !frappe.ui.form || !frappe.ui.form.ControlTime) {
        // Wait for frappe core to load if it's not ready yet
        setTimeout(init_time_patch, 100);
        return;
    }

    if (frappe.ui.form.ControlTime.prototype._time_patch_applied) return;
    frappe.ui.form.ControlTime.prototype._time_patch_applied = true;

    console.log("Time Patch: Applying circular clock overrides to ControlTime.");
        
        // 1. Disable Original Air Datepicker Logic
        frappe.ui.form.ControlTime.prototype.set_datepicker = function() {};
        
        // 2. Attach Bootstrap ClockPicker (Circular Design)
        frappe.ui.form.ControlTime.prototype.make_picker = function() {
            let me = this;
            this.$input.attr("placeholder", "hh:mm AM/PM");
            this.$input.clockpicker({
                placement: 'top',
                autoclose: true,
                twelvehour: true, // Render Circular Android Design with AM/PM toggle
                donetext: 'Done',
                afterDone: () => {
                    // ClockPicker natively forces inner values to 24-hr layout during selection.
                    // We immediately visually force it back to standard 12-hour AM/PM layout for the UI.
                    let val = me.$input.val();
                    if (val && !val.toLowerCase().includes('m')) {
                        let t = moment(val, 'HH:mm');
                        if (t.isValid()) {
                            me.$input.val(t.format('hh:mm A'));
                        }
                    }
                    me.parse_and_validate();
                    me.$input.trigger('change');
                }
            });
            this.refresh();
        };

        // 3. Database Integrity Parser (AM/PM String to 24hr Database String)
        frappe.ui.form.ControlTime.prototype.parse = function(value) {
            if (value) {
                if (value == "Invalid date") { return ""; }
                
                // Allow our specific 12-hour formats as well as legacy 24h ones
                let t = moment(value, ['hh:mm A', 'hh:mm a', 'h:mm a', 'HH:mm:ss', 'HH:mm']);
                if (t.isValid()) {
                    // Send strictly 24-hr formats to the python backend to prevent crash
                    return t.format('HH:mm:ss'); 
                }
                return value;
            }
        };

        // 4. Reverse Display Conversion (24hr Database String to AM/PM String)
        frappe.ui.form.ControlTime.prototype.format_for_input = function(value) {
            if (value) {
                // Time from DB might occasionally append microseconds (18:10:00.000000)
                let clean_val = value.split('.')[0];
                let t = moment(clean_val, ['HH:mm:ss', 'HH:mm', 'h:mm a', 'hh:mm A']);
                if (t.isValid()) {
                    return t.format('hh:mm A');
                }
                return value;
            }
            return "";
        };
        
        // 5. Override Validate to accept AM/PM values instead of hardcrashing
        frappe.ui.form.ControlTime.prototype.validate = function(value) {
            return value;
        };

        // 6. Global Formatter Override (Applies formatting to Read-Only forms, Grids, and Lists)
        function apply_formatters() {
            if (typeof frappe === "undefined") return;
            
            // 1. Standard Form formatters
            frappe.provide('frappe.form.formatters');
            frappe.form.formatters.Time = function(value) {
                if (value) {
                    let clean_val = value.split('.')[0];
                    let t = moment(clean_val, ['HH:mm:ss', 'HH:mm', 'h:mm a', 'hh:mm A']);
                    if (t.isValid()) {
                        return t.format('hh:mm A');
                    }
                }
                return value;
            };

            // 2. Global utils formatters (often used in Grids and Static HTML)
            frappe.provide('frappe.formatters');
            frappe.formatters.Time = frappe.form.formatters.Time;
        }

        apply_formatters();
        // Also re-apply on standard frappe events to be safe
        $(document).on('app_ready', apply_formatters);

        // 7. Intercept Form Load (Force UI redraw on default values)
        let original_set_input = frappe.ui.form.ControlTime.prototype.set_input;
        frappe.ui.form.ControlTime.prototype.set_input = function(value) {
            original_set_input.call(this, value);
            this.refresh_input_value();
        };

        frappe.ui.form.ControlTime.prototype.refresh_input_value = function() {
            if (this.value && this.$input) {
                let formatted = this.format_for_input(this.value);
                if (this.$input.val() !== formatted) {
                    this.$input.val(formatted);
                }
            }
        };

        // Ensure refresh also forces the correct format
        let original_refresh = frappe.ui.form.ControlTime.prototype.refresh;
        frappe.ui.form.ControlTime.prototype.refresh = function() {
            original_refresh.call(this);
            this.refresh_input_value();
        };

        // 9. THE NUCLEAR OPTION: Overriding frappe.format (The source of all UI display)
        function apply_nuclear_patch() {
            if (typeof frappe === "undefined") return;

            // Intercept the low-level format function
            if (frappe.format && !frappe.format._time_patch_applied) {
                let original_format = frappe.format;
                frappe.format = function(value, df, options, doc) {
                    if (df && (df.fieldtype === 'Time' || df.type === 'Time')) {
                        // Use our custom Time formatter for anything labeled as "Time"
                        return frappe.form.formatters.Time(value);
                    }
                    return original_format(value, df, options, doc);
                };
                frappe.format._time_patch_applied = true;
                console.log("Time Patch: Nuclear formatter intercept active.");
            }

            // Intercept time-specific string conversion
            if (frappe.datetime && frappe.datetime.str_to_user && !frappe.datetime.str_to_user._time_patch_applied) {
                let original_str_to_user = frappe.datetime.str_to_user;
                frappe.datetime.str_to_user = function(value, df) {
                    if (df && (df.fieldtype === 'Time' || df.type === 'Time')) {
                        return frappe.form.formatters.Time(value);
                    }
                    return original_str_to_user(value, df);
                };
                frappe.datetime.str_to_user._time_patch_applied = true;
            }
        }

        apply_nuclear_patch();
        $(document).on('app_ready', apply_nuclear_patch);

        console.log("Time Patch: Overrides successfully applied.");
}

// Start polling for frappe objects
init_time_patch();


