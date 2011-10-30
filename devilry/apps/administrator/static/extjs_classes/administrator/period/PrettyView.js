/** PrettyView for an period. */
Ext.define('devilry.administrator.period.PrettyView', {
    extend: 'devilry.administrator.PrettyView',
    alias: 'widget.administrator_periodprettyview',
    requires: [
        'devilry.statistics.PeriodAdminLayout'
    ],

    bodyTpl: Ext.create('Ext.XTemplate',
        '<div class="section">',
        '   <tpl if="is_old">',
        '       <div class="section warning">',
        '           <h1>Expired period</h1>',
        '           <p>',
        '               This period was active from <strong>{start_time:date}</strong> to ',
        '               <strong>{end_time:date}</strong>. Examiners do not have ',
        '               access to any data related to the period, including the ',
        '               feedback they have given to students. ',
        '               Students can still view all their deliveries and feedback.',
        '           </p>',
        '       </div>',
        '   </tpl>',
        '   <tpl if="starttime_in_future">',
        '       <div class="section warning">',
        '           <h1>In the future</h1>',
        '           <p>',
        '               This period has not yet started. Students and examiners ',
        '               can not access the period until its <strong>start time</strong>, which is ',
        '               <strong>{start_time:date}</strong>',
        '           </p>',
        '       </div>',
        '   </tpl>',
        '   <tpl if="is_active">',
        '       <div class="section ok">',
        '           <h1>Active</h1>',
        '           <p>',
        '               This period is currently active. It started <strong>{start_time:date}</strong> ',
        '               and it expires <strong>{end_time:date}</strong>. When the period expires, examiners ',
        '               will not have access to any data related to the period, including the ',
        '               feedback they have given to students.',
        '           </p>',
        '       </div>',
        '   </tpl>',
        '</div>'
    ),

    getExtraBodyData: function(record) {
        var is_old = record.data.end_time < Ext.Date.now();
        var starttime_in_future = record.data.start_time > Ext.Date.now();
        return {
            is_old: is_old,
            starttime_in_future: starttime_in_future,
            is_active: (!is_old && !starttime_in_future),
        };
    },

    initComponent: function() {
        Ext.apply(this, {
            relatedButtons: [{
                xtype: 'button',
                scale: 'large',
                text: 'Overview of all students',
                listeners: {
                    scope: this,
                    click: this._onPeriodOverview
                }
            }]
        });
        this.callParent(arguments);
        if(this.record) {
            this._onLoadRecord();
        } else {
            this.addListener('loadmodel', this._onLoadRecord, this);
        }
    },

    _onLoadRecord: function() {
        var querystring = Ext.Object.fromQueryString(window.location.search);
        if(querystring.open_overview === 'yes') {
            this._onPeriodOverview(
                querystring.overview_minimal === 'yes',
                querystring.overview_hidelabels === 'yes'
            );
        }
    },

    _onPeriodOverview: function(minimal_layout, hidelabels) {
        Ext.widget('window', {
            width: 800,
            height: 600,
            maximized: true,
            maximizable: true,
            layout: 'fit',
            items: {
                xtype: 'statistics-periodadminlayout',
                periodid: this.record.get('id'),
                minimal_layout: minimal_layout,
                hidelabels: hidelabels
            }
        }).show();
    }
});
