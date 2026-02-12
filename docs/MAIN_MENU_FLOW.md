# Main Menu Flow Documentation

## Overview

The Main Menu Flow is the primary entry point for the Sungrip Solar chatbot. It presents users with a menu of options and routes them to the appropriate flow based on their selection.

## Purpose

- Provide a clear entry point for new users
- Allow users to navigate to different services
- Make the chatbot more user-friendly and discoverable
- Follow conventions from morebnyemba/hanna and morebnyemba/Kalai-Safaris repositories

## Flow Structure

### Main Menu Flow (main_menu)

**Trigger Keywords**: menu, start, hello, hi, help, options

**Flow Steps**:
1. **Welcome** - Displays the main menu with 4 options
2. **Handle Choice** - Captures user's menu selection
3. **Route Steps** - Routes to appropriate sub-flows:
   - Option 1: Solar Quote Request Flow
   - Option 2: Installation Scheduling Flow
   - Option 3: Solar Packages Flow (NEW)
   - Option 4: Contact Support Flow (NEW)
4. **Invalid Choice** - Handles invalid inputs and prompts again

### Solar Packages Flow (solar_packages)

**Trigger Keywords**: packages, systems, options, what do you have

**Purpose**: Display available solar system packages with pricing and features

**Packages Shown**:
- Small Home Package (3kW) - $3,500
- Medium Home Package (5kW) - $5,500
- Large Home Package (8kW) - $8,500
- Small Business Package (10kW) - $10,500

**Flow Steps**:
1. **Welcome** - Displays all available packages with details
2. **Ask Interest** - Asks which package interests the user
3. **Provide Details** - Gives more information about selected package
4. **Route to Quote** - Offers to start quote request flow
5. **Switch to Quote** - Transitions to solar_quote_request flow
6. **Thank You** - Concludes if user doesn't want a quote

### Contact Support Flow (contact_support)

**Trigger Keywords**: support, help, contact, talk to human, agent

**Purpose**: Collect customer support requests and route to appropriate team

**Support Categories**:
1. Technical Issues
2. Billing Questions
3. Installation Support
4. Product Information
5. Other

**Flow Steps**:
1. **Welcome** - Shows support categories
2. **Ask Support Type** - Captures category selection
3. **Ask Details** - Collects detailed description of issue
4. **Ask Contact** - Gets preferred contact method
5. **Confirmation** - Confirms receipt and provides follow-up timeline

## Integration with Existing Flows

The new flows integrate seamlessly with existing flows:

- **Main Menu** routes to **Solar Quote Request** (existing)
- **Main Menu** routes to **Installation Scheduling** (existing)
- **Main Menu** routes to **Solar Packages** (new)
- **Main Menu** routes to **Contact Support** (new)
- **Solar Packages** can route to **Solar Quote Request**

## Loading the Flows

### Option 1: Load All Flows
```bash
cd backend
python manage.py load_flow_definitions
```

### Option 2: Load Specific Flows
```bash
# Load only main menu
python manage.py create_flow --flow=main_menu

# Load solar packages flow
python manage.py create_flow --flow=solar_packages

# Load contact support flow
python manage.py create_flow --flow=contact_support

# Load all flows
python manage.py create_flow --flow=all
```

## Data Models

These flows use the existing data models:

- `Flow` - Represents each conversational flow
- `FlowStep` - Individual steps within a flow
- `FlowTransition` - Conditional transitions between steps
- `FlowSession` - Active user sessions
- `SolarPackage` - Pre-configured solar packages (existing model)
- `PackageItem` - Items in solar packages (existing model)

## Benefits

1. **Better User Experience**: Clear navigation from a central menu
2. **Discoverability**: Users can explore all available services
3. **Flexibility**: Easy to add new flows/options in the future
4. **Convention Alignment**: Follows patterns from reference repositories
5. **Package Showcase**: Dedicated flow to display solar packages with pricing
6. **Support Integration**: Direct path for customers to get help

## Future Enhancements

Potential improvements:
- Add payment plan inquiry flow
- Add FAQ/Knowledge Base flow
- Add order tracking flow
- Add maintenance request flow
- Integration with WhatsApp interactive buttons for better UX
- Dynamic package pricing from database

## Testing

To test the flows:

1. Load the flows into the database
2. Create a test contact in the system
3. Start a flow session with the main_menu flow
4. Verify each option routes correctly
5. Test invalid inputs and error handling
6. Verify context variables are saved correctly

## Notes

- All flows include proper error handling for invalid inputs
- Context variables are used to track user choices
- Flows can be activated/deactivated without code changes
- The main menu flow is set as active by default
- Support flow collects detailed information for ticket creation
- Package flow includes pricing aligned with SolarPackage model
