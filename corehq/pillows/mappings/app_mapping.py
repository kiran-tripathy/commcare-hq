APP_INDEX="hqapps_5bdde176ed6648ad216b1e8b0ff00e6c"
APP_MAPPING={'_meta': {'comment': 'Autogenerated [corehq.apps.app_manager.models.Application] mapping from ptop_generate_mapping 11/07/2013',
           'created': None},
 'date_detection': False,
 'date_formats': ['yyyy-MM-dd',
                  "yyyy-MM-dd'T'HH:mm:ssZZ",
                  "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
                  "yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'",
                  "yyyy-MM-dd'T'HH:mm:ss'Z'",
                  "yyyy-MM-dd'T'HH:mm:ssZ",
                  "yyyy-MM-dd'T'HH:mm:ssZZ'Z'",
                  "yyyy-MM-dd'T'HH:mm:ss.SSSZZ",
                  "yyyy-MM-dd'T'HH:mm:ss",
                  "yyyy-MM-dd' 'HH:mm:ss",
                  "yyyy-MM-dd' 'HH:mm:ss.SSSSSS",
                  "mm/dd/yy' 'HH:mm:ss"],
 'dynamic': False,
 'properties': {'admin_password': {'type': 'string'},
                'admin_password_charset': {'type': 'string'},
                'application_version': {'type': 'string'},
                'attribution_notes': {'type': 'string'},
                'build_broken': {'type': 'boolean'},
                'build_comment': {'type': 'string'},
                'build_langs': {'type': 'string'},
                'build_signed': {'type': 'boolean'},
                'build_spec': {'dynamic': False,
                               'properties': {'build_number': {'type': 'long'},
                                              'doc_type': {'index': 'not_analyzed',
                                                           'type': 'string'},
                                              'latest': {'type': 'boolean'},
                                              'version': {'type': 'string'}},
                               'type': 'object'},
                'built_on': {'format': "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ssZZ||yyyy-MM-dd'T'HH:mm:ss.SSSSSS||yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'||yyyy-MM-dd'T'HH:mm:ss'Z'||yyyy-MM-dd'T'HH:mm:ssZ||yyyy-MM-dd'T'HH:mm:ssZZ'Z'||yyyy-MM-dd'T'HH:mm:ss.SSSZZ||yyyy-MM-dd'T'HH:mm:ss||yyyy-MM-dd' 'HH:mm:ss||yyyy-MM-dd' 'HH:mm:ss.SSSSSS||mm/dd/yy' 'HH:mm:ss",
                             'type': 'date'},
                'built_with': {'dynamic': False,
                               'properties': {'build_number': {'type': 'long'},
                                              'datetime': {'format': "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ssZZ||yyyy-MM-dd'T'HH:mm:ss.SSSSSS||yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'||yyyy-MM-dd'T'HH:mm:ss'Z'||yyyy-MM-dd'T'HH:mm:ssZ||yyyy-MM-dd'T'HH:mm:ssZZ'Z'||yyyy-MM-dd'T'HH:mm:ss.SSSZZ||yyyy-MM-dd'T'HH:mm:ss||yyyy-MM-dd' 'HH:mm:ss||yyyy-MM-dd' 'HH:mm:ss.SSSSSS||mm/dd/yy' 'HH:mm:ss",
                                                           'type': 'date'},
                                              'doc_type': {'index': 'not_analyzed',
                                                           'type': 'string'},
                                              'latest': {'type': 'boolean'},
                                              'signed': {'type': 'boolean'},
                                              'version': {'type': 'string'}},
                               'type': 'object'},
                'cached_properties': {'dynamic': False, 'type': 'object'},
                'case_sharing': {'type': 'boolean'},
                'cloudcare_enabled': {'type': 'boolean'},
                'comment_from': {'type': 'string'},
                'copy_history': {'type': 'string'},
                'copy_of': {'type': 'string'},
                'cp_is_active': {'type': 'boolean'},
                'created_from_template': {'type': 'string'},
                'deployment_date': {'format': "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ssZZ||yyyy-MM-dd'T'HH:mm:ss.SSSSSS||yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'||yyyy-MM-dd'T'HH:mm:ss'Z'||yyyy-MM-dd'T'HH:mm:ssZ||yyyy-MM-dd'T'HH:mm:ssZZ'Z'||yyyy-MM-dd'T'HH:mm:ss.SSSZZ||yyyy-MM-dd'T'HH:mm:ss||yyyy-MM-dd' 'HH:mm:ss||yyyy-MM-dd' 'HH:mm:ss.SSSSSS||mm/dd/yy' 'HH:mm:ss",
                                    'type': 'date'},
                'description': {'type': 'string'},
                'doc_type': {'index': 'not_analyzed', 'type': 'string'},
                'domain': {'type': 'string'},
                'force_http': {'type': 'boolean'},
                'is_released': {'type': 'boolean'},
                'langs': {'type': 'string'},
                'modules': {'dynamic': False,
                            'properties': {'case_label': {'dynamic': False,
                                                          'type': 'object'},
                                           'case_list': {'dynamic': False,
                                                         'properties': {'doc_type': {'index': 'not_analyzed',
                                                                                     'type': 'string'},
                                                                        'label': {'dynamic': False,
                                                                                  'type': 'object'},
                                                                        'show': {'type': 'boolean'}},
                                                         'type': 'object'},
                                           'case_type': {'type': 'string'},
                                           'details': {'dynamic': False,
                                                       'properties': {'columns': {'dynamic': False,
                                                                                  'properties': {'advanced': {'type': 'string'},
                                                                                                 'doc_type': {'index': 'not_analyzed',
                                                                                                              'type': 'string'},
                                                                                                 'enum': {'dynamic': False,
                                                                                                          'properties': {'doc_type': {'index': 'not_analyzed',
                                                                                                                                      'type': 'string'},
                                                                                                                         'key': {'type': 'string'},
                                                                                                                         'value': {'dynamic': False,
                                                                                                                                   'type': 'object'}},
                                                                                                          'type': 'object'},
                                                                                                 'field': {'type': 'string'},
                                                                                                 'filter_xpath': {'type': 'string'},
                                                                                                 'format': {'type': 'string'},
                                                                                                 'header': {'dynamic': False,
                                                                                                            'type': 'object'},
                                                                                                 'late_flag': {'type': 'long'},
                                                                                                 'model': {'type': 'string'},
                                                                                                 'time_ago_interval': {'type': 'float'}},
                                                                                  'type': 'object'},
                                                                      'doc_type': {'index': 'not_analyzed',
                                                                                   'type': 'string'},
                                                                      'sort_elements': {'dynamic': False,
                                                                                        'properties': {'direction': {'type': 'string'},
                                                                                                       'doc_type': {'index': 'not_analyzed',
                                                                                                                    'type': 'string'},
                                                                                                       'field': {'type': 'string'},
                                                                                                       'type': {'type': 'string'}},
                                                                                        'type': 'object'},
                                                                      'filter': {'type': 'string'},
                                                                      'type': {'type': 'string'}},
                                                       'type': 'object'},
                                           'doc_type': {'index': 'not_analyzed',
                                                        'type': 'string'},
                                           'forms': {'dynamic': False,
                                                     'properties': {'actions': {'dynamic': False,
                                                                                'properties': {'case_preload': {'dynamic': False,
                                                                                                                'properties': {'condition': {'dynamic': False,
                                                                                                                                             'properties': {'answer': {'type': 'string'},
                                                                                                                                                            'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                         'type': 'string'},
                                                                                                                                                            'question': {'type': 'string'},
                                                                                                                                                            'type': {'type': 'string'}},
                                                                                                                                             'type': 'object'},
                                                                                                                               'doc_type': {'index': 'not_analyzed',
                                                                                                                                            'type': 'string'},
                                                                                                                               'preload': {'dynamic': False,
                                                                                                                                           'type': 'object'}},
                                                                                                                'type': 'object'},
                                                                                               'close_case': {'dynamic': False,
                                                                                                              'properties': {'condition': {'dynamic': False,
                                                                                                                                           'properties': {'answer': {'type': 'string'},
                                                                                                                                                          'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                       'type': 'string'},
                                                                                                                                                          'question': {'type': 'string'},
                                                                                                                                                          'type': {'type': 'string'}},
                                                                                                                                           'type': 'object'},
                                                                                                                             'doc_type': {'index': 'not_analyzed',
                                                                                                                                          'type': 'string'}},
                                                                                                              'type': 'object'},
                                                                                               'close_referral': {'dynamic': False,
                                                                                                                  'properties': {'condition': {'dynamic': False,
                                                                                                                                               'properties': {'answer': {'type': 'string'},
                                                                                                                                                              'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                           'type': 'string'},
                                                                                                                                                              'question': {'type': 'string'},
                                                                                                                                                              'type': {'type': 'string'}},
                                                                                                                                               'type': 'object'},
                                                                                                                                 'doc_type': {'index': 'not_analyzed',
                                                                                                                                              'type': 'string'}},
                                                                                                                  'type': 'object'},
                                                                                               'doc_type': {'index': 'not_analyzed',
                                                                                                            'type': 'string'},
                                                                                               'open_case': {'dynamic': False,
                                                                                                             'properties': {'condition': {'dynamic': False,
                                                                                                                                          'properties': {'answer': {'type': 'string'},
                                                                                                                                                         'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                      'type': 'string'},
                                                                                                                                                         'question': {'type': 'string'},
                                                                                                                                                         'type': {'type': 'string'}},
                                                                                                                                          'type': 'object'},
                                                                                                                            'doc_type': {'index': 'not_analyzed',
                                                                                                                                         'type': 'string'},
                                                                                                                            'external_id': {'type': 'string'},
                                                                                                                            'name_path': {'type': 'string'}},
                                                                                                             'type': 'object'},
                                                                                               'open_referral': {'dynamic': False,
                                                                                                                 'properties': {'condition': {'dynamic': False,
                                                                                                                                              'properties': {'answer': {'type': 'string'},
                                                                                                                                                             'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                          'type': 'string'},
                                                                                                                                                             'question': {'type': 'string'},
                                                                                                                                                             'type': {'type': 'string'}},
                                                                                                                                              'type': 'object'},
                                                                                                                                'doc_type': {'index': 'not_analyzed',
                                                                                                                                             'type': 'string'},
                                                                                                                                'followup_date': {'type': 'string'},
                                                                                                                                'name_path': {'type': 'string'}},
                                                                                                                 'type': 'object'},
                                                                                               'referral_preload': {'dynamic': False,
                                                                                                                    'properties': {'condition': {'dynamic': False,
                                                                                                                                                 'properties': {'answer': {'type': 'string'},
                                                                                                                                                                'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                             'type': 'string'},
                                                                                                                                                                'question': {'type': 'string'},
                                                                                                                                                                'type': {'type': 'string'}},
                                                                                                                                                 'type': 'object'},
                                                                                                                                   'doc_type': {'index': 'not_analyzed',
                                                                                                                                                'type': 'string'},
                                                                                                                                   'preload': {'dynamic': False,
                                                                                                                                               'type': 'object'}},
                                                                                                                    'type': 'object'},
                                                                                               'subcases': {'dynamic': False,
                                                                                                            'properties': {'case_name': {'type': 'string'},
                                                                                                                           'case_properties': {'dynamic': False,
                                                                                                                                               'type': 'object'},
                                                                                                                           'case_type': {'type': 'string'},
                                                                                                                           'condition': {'dynamic': False,
                                                                                                                                         'properties': {'answer': {'type': 'string'},
                                                                                                                                                        'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                     'type': 'string'},
                                                                                                                                                        'question': {'type': 'string'},
                                                                                                                                                        'type': {'type': 'string'}},
                                                                                                                                         'type': 'object'},
                                                                                                                           'doc_type': {'index': 'not_analyzed',
                                                                                                                                        'type': 'string'},
                                                                                                                           'reference_id': {'type': 'string'},
                                                                                                                           'repeat_context': {'type': 'string'}},
                                                                                                            'type': 'object'},
                                                                                               'update_case': {'dynamic': False,
                                                                                                               'properties': {'condition': {'dynamic': False,
                                                                                                                                            'properties': {'answer': {'type': 'string'},
                                                                                                                                                           'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                        'type': 'string'},
                                                                                                                                                           'question': {'type': 'string'},
                                                                                                                                                           'type': {'type': 'string'}},
                                                                                                                                            'type': 'object'},
                                                                                                                              'doc_type': {'index': 'not_analyzed',
                                                                                                                                           'type': 'string'},
                                                                                                                              'update': {'dynamic': False,
                                                                                                                                         'type': 'object'}},
                                                                                                               'type': 'object'},
                                                                                               'update_referral': {'dynamic': False,
                                                                                                                   'properties': {'condition': {'dynamic': False,
                                                                                                                                                'properties': {'answer': {'type': 'string'},
                                                                                                                                                               'doc_type': {'index': 'not_analyzed',
                                                                                                                                                                            'type': 'string'},
                                                                                                                                                               'question': {'type': 'string'},
                                                                                                                                                               'type': {'type': 'string'}},
                                                                                                                                                'type': 'object'},
                                                                                                                                  'doc_type': {'index': 'not_analyzed',
                                                                                                                                               'type': 'string'},
                                                                                                                                  'followup_date': {'type': 'string'}},
                                                                                                                   'type': 'object'}},
                                                                                'type': 'object'},
                                                                    'doc_type': {'index': 'not_analyzed',
                                                                                 'type': 'string'},
                                                                    'form_filter': {'type': 'string'},
                                                                    'form_type': {'type': 'string'},
                                                                    'name': {'dynamic': False,
                                                                             'type': 'object'},
                                                                    'requires': {'type': 'string'},
                                                                    'show_count': {'type': 'boolean'},
                                                                    'unique_id': {'type': 'string'},
                                                                    'version': {'type': 'long'},
                                                                    'xmlns': {'type': 'string'}},
                                                     'type': 'object'},
                                           'name': {'dynamic': False,
                                                    'type': 'object'},
                                           'parent_select': {'dynamic': False,
                                                             'properties': {'active': {'type': 'boolean'},
                                                                            'doc_type': {'index': 'not_analyzed',
                                                                                         'type': 'string'},
                                                                            'module_id': {'type': 'string'},
                                                                            'relationship': {'type': 'string'}},
                                                             'type': 'object'},
                                           'put_in_root': {'type': 'boolean'},
                                           'referral_label': {'dynamic': False,
                                                              'type': 'object'},
                                           'referral_list': {'dynamic': False,
                                                             'properties': {'doc_type': {'index': 'not_analyzed',
                                                                                         'type': 'string'},
                                                                            'label': {'dynamic': False,
                                                                                      'type': 'object'},
                                                                            'show': {'type': 'boolean'}},
                                                             'type': 'object'},
                                           'task_list': {'dynamic': False,
                                                         'properties': {'doc_type': {'index': 'not_analyzed',
                                                                                     'type': 'string'},
                                                                        'label': {'dynamic': False,
                                                                                  'type': 'object'},
                                                                        'show': {'type': 'boolean'}},
                                                         'type': 'object'},
                                           'unique_id': {'type': 'string'}},
                            'type': 'object'},
                'multimedia_map': {'dynamic': False,
                                   'properties': {'doc_type': {'index': 'not_analyzed',
                                                               'type': 'string'},
                                                  'media_type': {'type': 'string'},
                                                  'multimedia_id': {'type': 'string'},
                                                  'output_size': {'dynamic': False,
                                                                  'type': 'object'},
                                                  'unique_id': {'type': 'string'},
                                                  'version': {'type': 'long'}},
                                   'type': 'object'},
                'name': {'fields': {'exact': {'index': 'not_analyzed',
                                              'type': 'string'},
                                    'name': {'index': 'analyzed',
                                             'type': 'string'}},
                         'type': 'multi_field'},
                'phone_model': {'type': 'string'},
                'platform': {'type': 'string'},
                'profile': {'dynamic': True, 'type': 'object'},
                'recipients': {'type': 'string'},
                'secure_submissions': {'type': 'boolean'},
                'short_odk_media_url': {'type': 'string'},
                'short_odk_url': {'type': 'string'},
                'short_url': {'type': 'string'},
                'show_user_registration': {'type': 'boolean'},
                'success_message': {'dynamic': False, 'type': 'object'},
                'text_input': {'type': 'string'},
                'translation_strategy': {'type': 'string'},
                'translations': {'dynamic': False, 'type': 'object'},
                'use_custom_suite': {'type': 'boolean'},
                'user_registration': {'dynamic': False,
                                      'properties': {'data_paths': {'dynamic': False,
                                                                    'type': 'object'},
                                                     'doc_type': {'index': 'not_analyzed',
                                                                  'type': 'string'},
                                                     'form_type': {'type': 'string'},
                                                     'name': {'dynamic': False,
                                                              'type': 'object'},
                                                     'password_path': {'type': 'string'},
                                                     'show_count': {'type': 'boolean'},
                                                     'unique_id': {'type': 'string'},
                                                     'username_path': {'type': 'string'},
                                                     'version': {'type': 'long'},
                                                     'xmlns': {'type': 'string'}},
                                      'type': 'object'},
                'user_type': {'type': 'string'},
                'version': {'type': 'long'}}}
