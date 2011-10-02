Ext.define('devilry.administrator.studentsmanager.StudentsManager', {
    extend: 'devilry.extjshelpers.studentsmanager.StudentsManager',
    alias: 'widget.administrator_studentsmanager',
    requires: [
        'devilry.extjshelpers.studentsmanager.ImportGroupsFromAnotherAssignment'
    ],

    mixins: {
        manageExaminers: 'devilry.administrator.studentsmanager.StudentsManagerManageExaminers',
        createGroups: 'devilry.administrator.studentsmanager.StudentsManagerManageGroups',
        loadRelatedUsers: 'devilry.administrator.studentsmanager.LoadRelatedUsersMixin'
    },

    //config: {
        //assignmentgroupPrevApprovedStore: undefined
    //},

    constructor: function(config) {
        this.initConfig(config);
        this.callParent([config]);
    },

    initComponent: function() {
        this.addStudentsButton = Ext.widget('button', {
            text: 'Create groups',
            iconCls: 'icon-add-32',
            scale: 'large',
            menu: [{
                text: Ext.String.format('One group for each student registered in {0}', DevilrySettings.DEVILRY_SYNCSYSTEM),
                listeners: {
                    scope: this,
                    click: this.onOneGroupForEachRelatedStudent
                }
            }, {
                text: 'Import from another assignment',
                listeners: {
                    scope: this,
                    click: this.onImportGroupsFromAnotherAssignmentInCurrentPeriod
                }
            }, {
                text: 'Manually',
                listeners: {
                    scope: this,
                    click: this.onManuallyCreateUsers
                }
            }]
        });

        this.callParent(arguments);
    },

    getToolbarItems: function() {
        var defaults = this.callParent();
        Ext.Array.insert(defaults, 2, [this.addStudentsButton, {
            xtype: 'button',
            text: 'Set examiners',
            scale: 'large',
            menu: this.getSetExaminersMenuItems()
        }]);
        return defaults;
    },

    getSetExaminersMenuItems: function() {
        return [{
            text: 'Replace',
            iconCls: 'icon-edit-16',
            listeners: {
                scope: this,
                click: this.onReplaceExaminers
            }
        }, {
            text: 'Add',
            iconCls: 'icon-add-16',
            listeners: {
                scope: this,
                click: this.onAddExaminers
            }
        }, {
            text: 'Random distribute',
            listeners: {
                scope: this,
                click: this.onRandomDistributeExaminers
            }
        }, {
            text: 'Copy from another assignment',
            listeners: {
                scope: this,
                click: this.onImportExaminersFromAnotherAssignmentInCurrentPeriod
            }
        }, {
            text: 'Match tagged examiners to equally tagged groups',
            listeners: {
                scope: this,
                click: this.onSetExaminersFromTags
            }
        }, {
            text: 'Clear',
            iconCls: 'icon-delete-16',
            listeners: {
                scope: this,
                click: this.onClearExaminers
            }
        }];
    },

    getContexMenuManySelectItems: function() {
        var defaultItems = this.callParent();
        return Ext.Array.merge(defaultItems, [{
            text: 'Set examiners',
            menu: this.getSetExaminersMenuItems()
        }]);
    },

    getFilters: function() {
        var defaultFilters = this.callParent();
        var me = this;
        var adminFilters = [{xtype: 'menuheader', html: 'Missing users'}, {
            text: 'Has no students',
            handler: function() { me.setFilter('candidates__student__username:none'); }
        }, {
            text: 'Has no examiners',
            handler: function() { me.setFilter('examiners__username:none'); }
        }];
        Ext.Array.insert(adminFilters, 0, defaultFilters);
        return adminFilters;
    },

    getOnSingleMenuItems: function() {
        var menu = this.callParent();
        menu.push({
            text: 'Change group members',
            iconCls: 'icon-edit-16',
            listeners: {
                scope: this,
                click: this.onChangeGroupMembers
            }
        });
        menu.push({
            text: 'Change group name',
            iconCls: 'icon-edit-16',
            listeners: {
                scope: this,
                click: this.onChangeGroupName
            }
        });
        return menu;
    },

    getOnManyMenuItems: function() {
        var menu = this.callParent();
        menu.push({
            text: 'Mark as delivered in a previous period',
            listeners: {
                scope: this,
                click: this.onPreviouslyPassed
            }
        });
        menu.push({
            text: 'Delete',
            iconCls: 'icon-delete-16',
            listeners: {
                scope: this,
                click: this.onDeleteGroups
            }
        });
        return menu;
    },


    statics: {
        getAllGroupsInAssignment: function(assignmentid, action) {
            assignmentGroupModel = Ext.ModelManager.getModel('devilry.apps.administrator.simplified.SimplifiedAssignmentGroupImport');
            var assignmentGroupStore = Ext.create('Ext.data.Store', {
                model: assignmentGroupModel,
                proxy: Ext.create('devilry.extjshelpers.RestProxy', {
                    url: assignmentGroupModel.proxy.url
                })
            });
            assignmentGroupStore.proxy.setDevilryResultFieldgroups(['users']);

            assignmentGroupStore.proxy.setDevilryFilters([{
                field: 'parentnode',
                comp: 'exact',
                value: assignmentid
            }]);

            assignmentGroupStore.pageSize = 1;
            assignmentGroupStore.load({
                scope: this,
                callback: function(records, op, success) {
                    if(!success) {
                        this.loadAssignmentGroupStoreFailed();
                    }
                    assignmentGroupStore.pageSize = assignmentGroupStore.totalCount;
                    assignmentGroupStore.load({
                        scope: this,
                        callback: function(records, op, success) {
                            Ext.bind(action.callback, action.scope, action.extraArgs, true)(records, op, success);
                        }
                    });
                }
            });
        }
    }
});
