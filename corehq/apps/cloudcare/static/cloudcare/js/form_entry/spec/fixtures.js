hqDefine("cloudcare/js/form_entry/spec/fixtures", function () {
    return {
        textJSON: (options={}) => (_.defaults(options, {
            "caption_audio": null,
            "caption_video": null,
            "caption_image": null,
            "caption_markdown": null,
            "caption": "name",
            "binding": "/data/name",
            "question_id": "name",
            "required": 0,
            "relevant": 0,
            "answer": null,
            "datatype": "str",
            "style": null,
            "type": "question",
            "ix": "0",
            "choices": null,
            "repeatable": null,
            "exists": null,
            "header": null,
            "control": 1,
            "help": null,
            "hint": null,
            "output": null,
            "add-choice": null
        })),

        selectJSON: (options={}) => (_.defaults(options, {
            "caption_audio": null,
            "caption_video": null,
            "caption_image": null,
            "caption_markdown": null,
            "caption": "choice",
            "binding": "/data/select",
            "question_id": "select",
            "required": 0,
            "relevant": 0,
            "answer": null,
            "datatype": "select",
            "style": null,
            "type": "question",
            "ix": "2",
            "choices": ["a", "b"],
            "repeatable": null,
            "exists": null,
            "header": null,
            "control": 2,
            "help": null,
            "hint": null,
            "output": null,
            "add-choice": null
        })),

        labelJSON: (options={}) => (_.defaults(options, {
            "caption_audio": null,
            "caption_video": null,
            "caption_image": null,
            "caption_markdown": null,
            "caption": "Label",
            "binding": "/data/label",
            "question_id": "label",
            "required": 0,
            "relevant": 0,
            "answer": null,
            "datatype": "info",
            "style": {"raw": "minimal"},
            "type": "question",
            "ix": "3",
            "choices": null,
            "repeatable": null,
            "exists": null,
            "header": null,
            "control": 9,
            "help": null,
            "hint": null,
            "output": null,
            "add-choice": null
        })),

        repeatJSON: (options={}) => (_.defaults(options, {
            "caption_audio": null,
            "caption": "Repeater",
            "caption_image": null,
            "type": "repeat-juncture",
            "caption_markdown": null,
            "ix": "0J",
            "relevant": 1,
            "main-header": "Repeater",
            "children": [],
            "add-choice": "None - Add Repeater",
            "caption_video": null,
        })),

        repeatNestJSON: () => ({
            "caption_audio": null,
            "caption": "Repeat Simple",
            "caption_image": null,
            "type": "repeat-juncture",
            "caption_markdown": null,
            "ix": "0J",
            "relevant": 1,
            "children": [{
                "caption": "Repeat Simple 1/1",
                "type": "sub-group",
                "uuid": "ed3f01b37034",
                "ix": "0:0",
                "children": [{
                    "caption_audio": null,
                    "caption": "Text_Question",
                    "binding": "/data/repeat/Text_Question",
                    "caption_image": null,
                    "type": "question",
                    "caption_markdown": null,
                    "required": 0,
                    "ix": "0:0,0",
                    "relevant": 1,
                    "help": null,
                    "answer": null,
                    "datatype": "str",
                    "style": {},
                    "caption_video": null,
                }],
                "repeatable": 1,
            }],
            "add-choice": "Add another Repeat Simple",
            "header": "Repeat Simple",
            "caption_video": null,
        }),

        groupJSON: (options={}) => (_.defaults(options, {
            "type": "sub-group",
            "ix": "1",
            "children": [
                {
                    "type": "sub-group",
                    "ix": "1,2",
                    "children": [
                        {
                            "type": "question",
                            "ix": "2,3",
                            "datatype": "str",
                            "answer": null,
                            "children": [],
                        },
                    ],
                },
            ],
        })),

        noQuestionGroupJSON: () => ({
            "type": "sub-group",
            "ix": "2",
            "children": [
                {
                    "type": "sub-group",
                    "ix": "2,2",
                    "children": [],
                },
            ],
        })

    };
});
