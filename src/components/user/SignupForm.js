import React from 'react';
import { Field, reduxForm } from 'redux-form';
import { Row, Col } from 'react-flexbox-grid/lib';
import { connect } from 'react-redux';
import { injectIntl } from 'react-intl';
import Recaptcha from 'react-recaptcha';
import { push } from 'react-router-redux';
import { signupUser, setLoginErrorMessage } from '../../actions/userActions';
import AppButton from '../common/AppButton';
import * as fetchConstants from '../../lib/fetchConstants';
import messages from '../../resources/messages';
import { emptyString } from '../../lib/formValidators';
import composeIntlForm from '../common/IntlForm';

const localMessages = {
  missingEmail: { id: 'user.missingEmail', defaultMessage: 'You need to enter your email address.' },
  missingFullname: { id: 'user.missingName', defaultMessage: 'You need to enter your full name.' },
  missingPassword: { id: 'user.missingPassword', defaultMessage: 'You need to enter your password.' },
  loginFailed: { id: 'user.loginFailed', defaultMessage: 'Your email or password was wrong.' },
  signUpNow: { id: 'user.signUpNow', defaultMessage: 'No account? Register now' },
};

const SignupForm = (props) => {
  const { handleSubmit, onSubmitSignupForm, fetchStatus, renderTextField } = props;
  const { formatMessage } = props.intl;
  return (
    <form onSubmit={handleSubmit(onSubmitSignupForm.bind(this))} className="signup-form">
      <Row>
        <Col lg={12}>
          <Field
            name="email"
            component={renderTextField}
            floatingLabelText={messages.userEmail}
          />
        </Col>
      </Row>
      <Row>
        <Col lg={12}>
          <Field
            name="password"
            type="password"
            component={renderTextField}
            floatingLabelText={messages.userPassword}
          />
        </Col>
      </Row>
      <Row>
        <Col lg={12}>
          <Field
            name="full_name"
            type="text"
            component={renderTextField}
            floatingLabelText={messages.userFullName}
          />
        </Col>
      </Row>
      <Row>
        <Col lg={12}>
          <Field
            name="notes"
            multiLine
            rows={2}
            rowsMax={4}
            component={renderTextField}
            floatingLabelText={messages.userNotes}
          />
        </Col>
      </Row>

      <Recaptcha
        sitekey="6Le8zhgUAAAAANfXdzoR0EFXNcjZnVTRhIh6JVnG"
      />

      <Row>
        <AppButton
          type="submit"
          label={formatMessage(messages.userSignup)}
          primary
          disabled={fetchStatus === fetchConstants.FETCH_ONGOING}
        />
        <Col lg={12}>
          <br />
          <a href="/#/login">
            <AppButton
              flat
              label={formatMessage(localMessages.signUpNow)}
            />
          </a>
        </Col>
      </Row>
    </form>
  );
};

SignupForm.propTypes = {
  // from composition
  intl: React.PropTypes.object.isRequired,
  location: React.PropTypes.object,
  redirect: React.PropTypes.string,
  handleSubmit: React.PropTypes.func.isRequired,
  renderTextField: React.PropTypes.func.isRequired,
  // from state
  fetchStatus: React.PropTypes.string.isRequired,
  errorMessage: React.PropTypes.string,
  // from dispatch
  onSubmitSignupForm: React.PropTypes.func.isRequired,
};

const mapStateToProps = state => ({
  fetchStatus: state.user.fetchStatus,
  errorMessage: state.user.errorMessage,
});

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmitSignupForm: (values) => {
    dispatch(signupUser(values))
    .then((response) => {
      if (response.status === 401) {
        dispatch(setLoginErrorMessage(ownProps.intl.formatMessage(localMessages.loginFailed)));
      } else {
        // redirect to destination if there is one
        const loc = ownProps.location;
        let redirect;
        if (ownProps.redirect) {
          redirect = ownProps.redirect;
        } else {
          redirect = (loc && loc.state && loc.state.nextPathname) ? loc.state.nextPathname : '';
        }
        if (redirect) {
          dispatch(push(redirect));
        }
      }
    });
  },
});

// in-browser validation callback
function validate(values) {
  const errors = {};
  if (emptyString(values.email)) {
    errors.email = localMessages.missingEmail;
  }
  if (emptyString(values.full_name)) {
    errors.email = localMessages.missingName;
  }
  if (emptyString(values.password)) {
    errors.password = localMessages.missingPassword;
  }
  return errors;
}

const reduxFormConfig = {
  form: 'signup-form',
  validate,
};

export default
  injectIntl(
    composeIntlForm(
      reduxForm(reduxFormConfig)(
        connect(mapStateToProps, mapDispatchToProps)(
          SignupForm
        )
      )
    )
  );
