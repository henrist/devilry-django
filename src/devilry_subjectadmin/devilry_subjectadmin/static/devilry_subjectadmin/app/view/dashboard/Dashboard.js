Ext.define('devilry_subjectadmin.view.dashboard.Dashboard' ,{
    extend: 'Ext.panel.Panel',
    alias: 'widget.dashboard',
    cls: 'dashboard',

    requires: [
        'devilry_subjectadmin.view.dashboard.AllActiveWhereIsAdminList'
    ],

    layout: 'column',
    frame: false,
    border: 0,
    bodyPadding: '20 40 20 40',
    autoScroll: true,

    items: [{
        xtype: 'container',
        columnWidth: 1,
        items: [{
            xtype: 'allactivewhereisadminlist'
        }, {
            xtype: 'box',
            cls: 'bootstrap',
            margin: '40 0 0 0',
            html: [
                '<h3 style="font-size: 18px; margin-bottom: 0px;">',
                    interpolate(gettext('Expired %(subjects_term)s'), {
                        subjects_term: gettext('subjects')
                    }, true),
                '</h3>',
                '<p style="margin-top: 0px; padding-top: 0;">',
                    '<a href="#/">',
                        gettext('Browse everything where you are administrator'),
                    '</a>',
                '</p>'
            ].join('')
        }]
    }, {
        xtype: 'container',
        width: 250,
        margin: '6 0 0 50',
        border: false,
        layout: 'anchor',
        items: [{
            xtype: 'box',
            cls: 'bootstrap',
            tpl: '<h4>{heading}</h4>',
            data: {
                heading: gettext('Interractive guides')
            }
        }, {
            xtype: 'guidesystemlist',
            guides: [{
                xtype: 'guide-createnewassignment',
                title: gettext('Create new assignment')
            }]
        }]
    }]
});
