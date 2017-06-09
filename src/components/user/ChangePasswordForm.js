import React from 'react';
import { Field, reduxForm } from 'redux-form';
import { Row, Col } from 'react-flexbox-grid/lib';
import { FormattedMessage } from 'react-intl';
import AppButton from '../common/AppButton';
import messages from '../../resources/messages';
import { emptyString, passwordTooShort, stringsDoNotMatch } from '../../lib/formValidators';
import composeIntlForm from '../common/IntlForm';

const localMessages = {
  missingOldPassword: { id: 'user.missingOldPassword', defaultMessage: 'You need to enter your old password.' },
  missingNewPassword: { id: 'user.missingNewPassword', defaultMessage: 'You need to enter a new password.' },
  failed: { id: 'user.passwordChange.failed', defaultMessage: 'Sorry, something went wrong.' },
};

const ChangePasswordContainer = (props) => {
  const { handleSubmit, onSubmit, pristine, submitting, renderTextField, titleMsg, buttonMsg, showOldPassword } = props;
  const { formatMessage } = props.intl;
  let oldPasswordContent = null;
  if (showOldPassword) {
    oldPasswordContent = (
      <Row>
        <Col lg={5}>
          <Field
            fullWidth
            name="old_password"
            type="password"
            component={renderTextField}
            floatingLabelText={messages.userOldPassword}
          />
        </Col>
      </Row>
    );
  }
  return (
    <form onSubmit={handleSubmit(onSubmit.bind(this))} className="app-form change-password-form">
      <Row>
        <Col lg={12}>
          <h1><FormattedMessage {...titleMsg} /></h1>
        </Col>
      </Row>
      {oldPasswordContent}
      <Row>
        <Col lg={5}>
          <Field
            fullWidth
            name="new_password"
            type="password"
            component={renderTextField}
            floatingLabelText={messages.userNewPassword}
          />
        </Col>
      </Row>
      <Row>
        <Col lg={5}>
          <Field
            fullWidth
            name="confirm_password"
            type="password"
            component={renderTextField}
            floatingLabelText={messages.userConfirmPassword}
          />
        </Col>
      </Row>
      <Row>
        <Col lg={12}>
          <AppButton
            type="submit"
            label={formatMessage(buttonMsg)}
            primary
            disabled={pristine || submitting}
          />
        </Col>
      </Row>
    </form>
  );
};

ChangePasswordContainer.propTypes = {
  // from composition
  intl: React.PropTypes.object.isRequired,
  location: React.PropTypes.object,
  redirect: React.PropTypes.string,
  handleSubmit: React.PropTypes.func.isRequired,
  renderTextField: React.PropTypes.func.isRequired,
  pristine: React.PropTypes.bool.isRequired,
  submitting: React.PropTypes.bool.isRequired,
  // from parent
  showOldPassword: React.PropTypes.bool,
  titleMsg: React.PropTypes.object.isRequired,
  buttonMsg: React.PropTypes.object.isRequired,
  onSubmit: React.PropTypes.func.isRequired,
};

// in-browser validation callback
function validate(values) {
  const errors = {};
  if (emptyString(values.old_password)) {
    errors.old_password = localMessages.missingOldPassword;
  }
  if (passwordTooShort(values.old_password)) {
    errors.old_password = messages.passwordTooShort;
  }
  if (emptyString(values.new_password)) {
    errors.new_password = localMessages.missingNewPassword;
  }
  if (passwordTooShort(values.new_password)) {
    errors.new_password = messages.passwordTooShort;
  }
  if (stringsDoNotMatch(values.new_password, values.confirm_password)) {
    errors.confirm_password = messages.passwordsMismatch;
  }
  return errors;
}

const reduxFormConfig = {
  form: 'change-password-form',
  validate,
};

export default
  composeIntlForm(
    reduxForm(reduxFormConfig)(
      ChangePasswordContainer
    )
  );
