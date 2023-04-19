def update_script():
    from corehq.form_processor.models import CommCareCase
    from corehq.apps.hqcase.case_helper import CaseHelper
    from corehq.apps.locations.models import SQLLocation
    import os

    DOMAIN = 'develop'
    CHILD_CASE_TYPE = 'membre'

    case_ids = CommCareCase.objects.get_case_ids_in_domain(domain=DOMAIN, type=CHILD_CASE_TYPE)

    total_cases = len(case_ids)
    cases_checked = -1

    log_file_path = os.path.expanduser("~/script.log")
    with open(log_file_path, "a") as logfile:
        for child_case in CommCareCase.objects.iter_cases(case_ids, domain=DOMAIN):
            # --- Statistics
            cases_checked += 1
            progress = round(cases_checked / total_cases, 3)
            print(f"{progress}% complete")
            # --------------

            child_case_helper = CaseHelper(domain=DOMAIN, case=child_case)
            
            """
                Step 2 - Make sure that the case properties of both the child and parent cases correspond to te
                village's hierarchy. The owner_id of both cases is the village id
            """
            try:
                parent_case = child_case.parent
                village_id = parent_case.owner_id
            except Exception:
                logfile.write(f"Skipped {child_case.case_id}. Reason: No parent case\n")
                continue

            try:
                village = SQLLocation.objects.filter(location_id=village_id, domain=DOMAIN).first()
                formation_sanitaire = village.parent
                arrondissement = formation_sanitaire.parent
                commune = arrondissement.parent
                zone_sanitaire = commune.parent
                departement = zone_sanitaire.parent
            except Exception as e:
                logfile.write(f"Skipped {child_case.case_id}. Reason: Location hierarchy issue. {e}\n")
                continue

            correct_properties = {
                "hh_village_name": village.name,
                "hh_formation_sanitaire_name": formation_sanitaire.name,
                "hh_arrondissement_name": arrondissement.name,
                "hh_commune_name": commune.name,
                "hh_zone_sanitaire_name": zone_sanitaire.name,
                "hh_departement_name": departement.name
            }

            parent_case_helper = CaseHelper(domain=DOMAIN, case=parent_case)
            case_helpers = (parent_case_helper, child_case_helper)
            cases = (parent_case, child_case)

            try:
                for case, case_helper in zip(cases, case_helpers):
                    is_dirty = False
                    updated_properties = {}
                    for property_name, correct_property_value in correct_properties.items():
                        curr_case_property_value = case.get_case_property(property_name)

                        if (not curr_case_property_value) or (curr_case_property_value != correct_property_value):
                            updated_properties[property_name] = correct_property_value
                            is_dirty = True
                    
                    update_dict = {'properties': updated_properties}
                    if case.case_id == child_case.case_id and case.owner_id != parent_case.owner_id:
                        is_dirty = True
                        update_dict['owner_id'] = parent_case.owner_id

                    if is_dirty:
                        case_helper.update(update_dict)
            except Exception as e:
                logfile.write(f"Skipped {child_case.case_id}. Reason: Cannot update case. {e}\n")
