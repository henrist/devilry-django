/** Singleton class with methods for form error parsing. No state is stored in
 * the singleton. */
Ext.define('themebase.form.ErrorUtils', {
    singleton: true,

    /**
     * Get errors from an ``Ext.data.Operation`` object.
     *
     * The returned object guaranteed to have the following attributes:
     *
     *  - **global**: Array of global errors.
     *  - **field**: Map of field errors with field name as key. The __all__
     *    key is removed, since devilry.restful adds this value to global
     *    as well.
     *
     *  @return an object as described above.
     */
    getErrorsFromOperation: function(operation) {
        var restfulErrors = this.getRestErrorsFromOperation(operation);
        if(restfulErrors) {
            return restfulErrors;
        } else {
            return {
                global: this.getErrorMessageFromOperation(operation),
                field: []
            };
        } 
    },

    /** Makes the errors messages contained in the ``responseData`` added to
     * ``Ext.data.Operation`` objects by
     * ``devilry.extjshelpers.RestProxy.setException``.
     *
     * The returned object guaranteed to have the following attributes (unless it is null):
     *
     *  - **global**: Array of global errors.
     *  - **field**: Object of field errors with field name as key. The __all__
     *    key is removed, since devilry.restful adds this value to global
     *    as well.
     *
     *  @return an object as described above, or null if no REST errormessages
     *  can be found in the operation object.
     */
    getRestErrorsFromOperation: function(operation) {
        if(operation.responseData && operation.responseData.items.errormessages) {
            var errors = operation.responseData.items;
            var fielderrors = {};
            if(errors.fielderrors) {
                Ext.Object.each(errors.fielderrors, function(key, value) {
                    if(key != '__all__') {
                        fielderrors[key] = value;
                    }
                });
            }
            return {
                global: errors.errormessages,
                field: fielderrors
            };
        } else {
            return null;
        }
    },

    /** Formats the error object returned by ``Ext.data.Operation.getError(). as
     * a string that can be displayed to users. */
    getErrorMessageFromOperation: function(operation) {
        var error = operation.getError();
        var message;
        if(error.status === 0) {
            message = dtranslate('themebase.lostserverconnection');
        } else {
            message = Ext.String.format('{0}: {1}', error.status, error.statusText);
        }
        return message;
    },

    _addGlobalErrorMessages: function(errormessages) {
        Ext.Array.each(errormessages, function(message) {
            this.add({
                message: message,
                type: 'error'
            });
        }, this);
    },
});
