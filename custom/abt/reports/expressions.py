import os
from jsonobject import JsonObject
import yaml
from corehq.apps.userreports.specs import TypeProperty
from corehq.apps.app_manager.models import Application
from dimagi.utils.decorators.memoized import memoized


class AbtSupervisorExpressionSpec(JsonObject):
    type = TypeProperty('abt_supervisor')
    _questions_cache = {}

    @property
    @memoized
    def _flag_specs(self):
        """
        Return a dict where keys are form xmlns and values are lists of FlagSpecs
        """
        path = os.path.join(os.path.dirname(__file__), 'flagspecs.yaml')
        with open(path) as f:
            return yaml.load(f)

    @classmethod
    def _get_val(cls, item, path):
        """
        Return the answer in the given submitted form (item) to the question specified by path.
        Return empty tuple if no answer was given to the given question.
        """
        if path:
            try:
                v = item['form']
                for key in path:
                    v = v[key]
                return v
            except KeyError:
                return ()

    @classmethod
    def _question_answered(cls, value):
        """
        Return true if the given value indicates that an answer was provided for its question.
        """
        return value != ()

    @classmethod
    def _raise_for_any_answer(cls, danger_value):
        """
        Return true if the given danger_value indicates that any question answer should raise the flag.
        """
        return danger_value == []

    @classmethod
    def _get_question_options(cls, item, question_path):
        """
        Return a list of option values for the given question path and item
        (which is a dict representation of an XFormInstance)
        """
        app_id, xmlns = item['app_id'], item['xmlns']
        questions = cls._questions_cache.get((app_id, xmlns), None)
        if questions is None:
            form = Application.get(app_id).get_form_by_xmlns(xmlns)
            questions = {
                q['value']: q for q in form.get_questions([], include_groups=True)
            }
            cls._questions_cache[(app_id, xmlns)] = questions

        question = questions.get('/data/' + "/".join(question_path), {})
        options = [o['value'] for o in question.get("options", [])]
        return options

    @classmethod
    def _get_unchecked(cls, xform_instance, question_path, answer, ignore=None):
        """
        Return the unchecked options in the given question.
        Do not return any which appear in the option ignore parameter.

        answer should be a string
        ignore should be a list of strings.
        """
        answer = answer or ""
        options = set(cls._get_question_options(xform_instance, question_path))
        checked = set(answer.split(" "))
        unchecked = options - checked
        ret = unchecked - set(ignore)
        return list(ret)

    @classmethod
    def _get_comments(cls, item, spec):
        """
        Return the comments for the question specified in the spec.
        If the spec does not contain a `comment` field, then the `question`
        field is used to build the path to the comment question.
        """
        comments_question = spec.get('comment', False)
        question_path = spec["question"]

        if not comments_question:
            parts = question_path[-1].split("_")
            parts.insert(1, "comments")
            comments_question = question_path[:-1] + ["_".join(parts)]

        comments = cls._get_val(item, comments_question)
        return comments if comments != () else ""

    @classmethod
    def _get_warning(cls, spec, item):
        country = cls._get_val(item, ["location_data", "country"])
        default = spec.get("warning", "")
        if country in ["Senegal", "Benin", "Mali", "Madagascar"]:
            return spec.get("french", default)
        return default

    @classmethod
    def _get_inspector_names(cls, item):
        repeat_items = cls._get_val(item, ['employee_group', 'employee'])
        if repeat_items == ():
            return ""
        if type(repeat_items) != list:
            repeat_items = [repeat_items]
        repeat_items = [{'form': x} for x in repeat_items]

        names = []
        for i in repeat_items:
            for q in ['other_abt_employee_name', 'abt_employee_name', 'other_non-abt_employee_name']:
                name = cls._get_val(i, ['abt_emp_list', q])
                if name:
                    names.append(name)
                    break

        return ", ".join(names)

    def __call__(self, item, context=None):
        """
        Given a document (item), return a list of documents representing each
        of the flagged questions.
        """
        names = self._get_inspector_names(item)
        docs = []
        for spec in self._flag_specs.get(item['xmlns'], []):

            if spec.get("base_path", False):
                repeat_items = self._get_val(item, spec['base_path'])
                if repeat_items == ():
                    repeat_items = []
                if type(repeat_items) != list:
                    # bases will be a dict if the repeat only happened once.
                    repeat_items = [repeat_items]
                # We have to add the 'form' key here so that _get_val works correctly.
                repeat_items = [{'form': x} for x in repeat_items]
            else:
                repeat_items = [item]

            # Iterate over the repeat items, or the single submission
            for partial in repeat_items:

                form_value = self._get_val(partial, spec['question'])
                warning_type = spec.get("warning_type", None)

                if warning_type == "unchecked" and form_value:
                    # Don't raise flag if no answer given
                    ignore = spec.get("ignore", [])
                    unchecked = self._get_unchecked(
                        item,
                        spec.get('base_path', []) + spec['question'],
                        form_value,
                        ignore
                    )
                    if unchecked:
                        # Raise a flag because there are unchecked answers.
                        docs.append({
                            'flag': spec['question'][-1],
                            'warning': self._get_warning(spec, item).format(msg=", ".join(unchecked)),
                            'comments': self._get_comments(partial, spec),
                            'names': names,
                        })

                if warning_type == "q3_special" and form_value:
                    # One of the questions doesn't follow the same format as the
                    # others, hence this special case.
                    missing_items = ""
                    if form_value == "only_license":
                        missing_items = "cell"
                    if form_value == "only_cell":
                        missing_items = "license"
                    if form_value == "none":
                        missing_items = "cell, license"
                    if missing_items:
                        docs.append({
                            'flag': spec['question'][-1],
                            'warning': self._get_warning(spec, item).format(msg=missing_items),
                            'comments': self._get_comments(partial, spec),
                            'names': names,
                        })

                else:
                    danger_value = spec.get('answer', [])
                    if form_value == danger_value or (
                        self._question_answered(form_value) and
                        self._raise_for_any_answer(danger_value)
                    ):
                        docs.append({
                            'flag': spec['question'][-1],
                            'warning': self._get_warning(spec, item).format(
                                msg=self._get_val(partial, spec.get('warning_question', None)) or ""
                            ),
                            'comments': self._get_comments(partial, spec),
                            'names': names,
                        })

        return docs


def abt_supervisor_expression(spec, context):
    wrapped = AbtSupervisorExpressionSpec.wrap(spec)
    return wrapped
