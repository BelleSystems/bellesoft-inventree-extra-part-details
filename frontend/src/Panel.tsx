// Import for type checking
import {
  checkPluginVersion,
  type InvenTreePluginContext
} from '@inventreedb/ui';
import { Alert, Flex, Paper, Stack, Table, Text, Title } from '@mantine/core';

// This is the function which is called by InvenTree to render the actual panel component
export function renderPartTotalPricePanel(context: InvenTreePluginContext) {
  checkPluginVersion(context);

  const total = context['context']['total_price'];
  const okTotal = context['context']['ok_total_price'];
  const damagedTotal = context['context']['damaged_total_price'];
  const currency = context['context']['currency'];
  const mixed = context['context']['mixed_currency'];
  const totalStock = context['context']['total_stock'];
  const okStock = context['context']['ok_stock'];
  const damagedStock = context['context']['damaged_stock'];
  const locationsData = context['context']['locations_data'] || {};

  const locationsArray = Object.values(locationsData).sort((a: any, b: any) => {
    // Put "No Location" items at the end
    if (a.location_id === null && b.location_id !== null) return 1;
    if (a.location_id !== null && b.location_id === null) return -1;

    const nameA = (a.location_path || a.location_name || '').toLowerCase();
    const nameB = (b.location_path || b.location_name || '').toLowerCase();
    return nameA.localeCompare(nameB);
  });

  return (
    <>
      <Stack>
        {locationsArray.length > 0 && (
          <Paper withBorder p='md'>
            <Title order={4} mb='sm'>
              Stock by Location
            </Title>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Location</Table.Th>
                  <Table.Th>Total</Table.Th>
                  <Table.Th>OK</Table.Th>
                  <Table.Th>Damaged</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {locationsArray.map((location: any, index: number) => (
                  <Table.Tr
                    key={location.location_id ?? `no-location-${index}`}
                  >
                    <Table.Td>
                      <Text fw={500}>
                        {location.location_path || location.location_name}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      {Number(location.total).toLocaleString()}
                    </Table.Td>
                    <Table.Td>
                      <Text c='green'>
                        {Number(location.ok).toLocaleString()}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text c='red'>
                        {Number(location.damaged).toLocaleString()}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Paper>
        )}

        <Flex>
          <Alert title='Total Stock'>
            {totalStock ? `${totalStock}` : 'None'}
          </Alert>
          <Alert title='Outlets Total'>{okStock ? `${okStock}` : 'None'}</Alert>
          <Alert title='Total Breakage'>
            {damagedStock ? `${damagedStock}` : 'None'}
          </Alert>
          <Alert title='Total Amount'>
            {mixed && (
              <div>Mixed currencies detected; showing partial sum.</div>
            )}
            {total
              ? `${currency ?? ''} ${Number(total).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : 'None'}
          </Alert>
          <Alert title='Outlet Total Amount'>
            {okTotal
              ? `${currency ?? ''} ${Number(okTotal).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : 'None'}
          </Alert>
          <Alert title='Breakages Total Amount'>
            {damagedTotal
              ? `${currency ?? ''} ${Number(damagedTotal).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : 'None'}
          </Alert>
        </Flex>
      </Stack>
    </>
  );
}
