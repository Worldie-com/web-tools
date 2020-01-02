import PropTypes from 'prop-types';
import React from 'react';
import { reduxForm, FieldArray, Field, propTypes } from 'redux-form';
import { injectIntl } from 'react-intl';
import withIntlForm from './hocs/IntlForm';
// import messages from '../../resources/messages';

const localMessages = {
  label: { id: 'system.label', defaultMessage: '{label}' },
  typeCrimson: { id: 'system.twitter.crimson', defaultMessage: 'Crimson Hexagon ID' },
};

const TwitterCheckboxSelector = ({ initialValues, renderCheckbox, renderTextField, onChange, intl: { formatMessage }, fields }) => (
  <ul>
    {fields.map((name, index, thisFieldArray) => { // redux-form overrides map, and converts name to a string instead of an object!
      const fieldObject = thisFieldArray.get(index);
      let chIdField = null;
      if (fieldObject.type === 'crimson') {
        chIdField = (
          <div>
            <Field // TODO maybe admin only...
              name="crimson_hexagon_id"
              component={renderTextField}
              label={formatMessage(localMessages.typeCrimson)}
            />
          </div>
        );
      }
      const content = (
        <li key={index}>
          <Field
            initialValues={initialValues}
            key={index}
            name={`${name}.label`}
            component={info => (
              <div>
                {renderCheckbox({
                  ...info,
                  label: formatMessage(localMessages.label, { label: fieldObject.label }),
                  input: {
                    ...info.input,
                    ...fieldObject,
                    value: fieldObject.selected,
                    onChange: newValue => onChange({ ...info.input, ...fieldObject, value: newValue }),
                  },
                })}
                { chIdField }
              </div>
            )}
            label={`${name}.label`}
          />
        </li>
      );
      return content;
    })}
  </ul>
);

TwitterCheckboxSelector.propTypes = {
  fields: PropTypes.object,
  initialValues: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
  renderCheckbox: PropTypes.func.isRequired,
  renderTextField: PropTypes.func.isRequired,
  intl: PropTypes.object,
  onChange: PropTypes.func,
};

const TwitterCheckboxList = injectIntl(withIntlForm(TwitterCheckboxSelector));

const TwitterCheckboxFieldArray = (props) => {
  // merge w intialValues from previouslySelected
  const twitterSelected = [...props.initialValues];
  if (props.previouslySelected) {
    props.previouslySelected.forEach((p) => {
      const toUpdate = twitterSelected.findIndex(t => t.id === p.id);
      if (toUpdate > -1) {
        twitterSelected[toUpdate].selected = p.value;
        twitterSelected[toUpdate].value = p.value;
      }
    });
  }
  return (
    <div>
      <FieldArray
        name="channel"
        form={propTypes.form}
        component={TwitterCheckboxList}
        initialValues={{ channel: twitterSelected }}
        onChange={props.onChange}
      />
    </div>
  );
};

TwitterCheckboxFieldArray.propTypes = {
  // from parent
  intl: PropTypes.object.isRequired,
  name: PropTypes.string.isRequired,
  type: PropTypes.string,
  initialValues: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
  previouslySelected: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array,
  ]),
  onChange: PropTypes.func,
};

export default
injectIntl(
  withIntlForm(
    reduxForm({ propTypes })(
      TwitterCheckboxFieldArray
    )
  )
);