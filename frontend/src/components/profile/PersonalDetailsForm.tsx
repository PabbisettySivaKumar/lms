'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/axios';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

const schema = z.object({
    address: z.string().optional(),
    blood_group: z.string().optional(),
    father_name: z.string().optional(),
    father_dob: z.string().optional(),
    mother_name: z.string().optional(),
    mother_dob: z.string().optional(),
    spouse_name: z.string().optional(),
    spouse_dob: z.string().optional(),
    emergency_contact_name: z.string().optional(),
    emergency_contact_phone: z.string().optional(),
    dob: z.string().optional(),
    permanent_address: z.string().optional(),
    children_names: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function PersonalDetailsForm() {
    const { user, fetchUser } = useAuth();
    const [isLoading, setIsLoading] = useState(false);



    const {
        register,
        handleSubmit,
        reset,
        watch,
        setValue,
        getValues,
        formState: { errors }
    } = useForm<FormValues>({
        resolver: zodResolver(schema),
    });

    const [isEditing, setIsEditing] = useState(false);
    const [sameAsCurrent, setSameAsCurrent] = useState(false);

    // Watch address to update permanent if checked
    const currentAddress = watch('address');

    useEffect(() => {
        if (sameAsCurrent) {
            setValue('permanent_address', currentAddress);
        }
    }, [sameAsCurrent, currentAddress, setValue]);

    useEffect(() => {
        if (user) {
            reset({
                address: user.address || '',
                blood_group: user.blood_group || '',
                father_name: user.father_name || '',
                father_dob: user.father_dob || '',
                mother_name: user.mother_name || '',
                mother_dob: user.mother_dob || '',
                spouse_name: user.spouse_name || '',
                spouse_dob: user.spouse_dob || '',
                emergency_contact_name: user.emergency_contact_name || '',
                emergency_contact_phone: user.emergency_contact_phone || '',
                dob: user.dob || '',
                permanent_address: user.permanent_address || '',
                children_names: user.children_names || ''
            });

            if (user.address && user.permanent_address && user.address === user.permanent_address) {
                setSameAsCurrent(true);
            }
        }
    }, [user, reset]);

    const onSubmit = async (data: FormValues) => {
        setIsLoading(true);
        try {
            // Filter out empty strings and convert them to null/undefined for optional fields
            const payload: any = {};
            Object.keys(data).forEach((key) => {
                const value = data[key as keyof FormValues];
                // Only include non-empty values (empty strings are excluded)
                if (value !== '' && value !== null && value !== undefined) {
                    payload[key] = value;
                }
            });
            
            const response = await api.patch('/users/me', payload);
            toast.success('Profile updated successfully');
            await fetchUser();
            setIsEditing(false); // Exit edit mode
        } catch (error: any) {
            console.error('Error updating profile:', error);
            let errorMessage = 'Failed to update profile';
            
            if (error.response) {
                const detail = error.response.data?.detail;
                if (typeof detail === 'string') {
                    errorMessage = detail;
                } else if (Array.isArray(detail)) {
                    errorMessage = detail.map((err: any) => err.msg || err.message || JSON.stringify(err)).join(', ');
                } else if (detail && typeof detail === 'object') {
                    errorMessage = JSON.stringify(detail);
                } else if (error.response.status) {
                    errorMessage = `Error ${error.response.status}: ${error.response.statusText || 'Request failed'}`;
                }
            } else if (error.request) {
                errorMessage = 'No response from server. Please check your connection.';
            } else {
                errorMessage = error.message || 'An unexpected error occurred';
            }
            
            toast.error(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    const toggleEdit = (e: React.MouseEvent) => {
        e.preventDefault();
        setIsEditing(!isEditing);
        if (isEditing) {
            reset(); // Revert changes on cancel
        }
    };

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Personal Details</CardTitle>
                    <CardDescription>Manage your personal information</CardDescription>
                </div>
                {!isEditing && (
                    <Button variant="outline" onClick={(e) => { e.preventDefault(); setIsEditing(true); }}>
                        Edit Details
                    </Button>
                )}
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">

                    <fieldset disabled={!isEditing} className="space-y-6 group-disabled:opacity-100">
                        {/* Bio */}
                        <div>
                            <h3 className="text-sm font-semibold mb-3">Bio</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="blood">Blood Group</Label>
                                    <Input id="blood" placeholder="e.g. O+" {...register('blood_group')} disabled={!isEditing} />
                                </div>
                            </div>
                        </div>

                        {/* Contact */}
                        <div>
                            <h3 className="text-sm font-semibold mb-3">Contact</h3>
                            <div className="space-y-2">
                                <Label htmlFor="address">Current Address</Label>
                                <Textarea id="address" {...register('address')} placeholder="Full address" disabled={!isEditing} />
                            </div>
                        </div>

                        {/* Permanent Address */}
                        <div>
                            <div className="flex items-center space-x-2 mb-3">
                                <Checkbox
                                    id="sameAs"
                                    checked={sameAsCurrent}
                                    onCheckedChange={(checked) => {
                                        setSameAsCurrent(checked === true);
                                        if (checked === true) setValue('permanent_address', getValues('address'));
                                    }}
                                    disabled={!isEditing}
                                />
                                <Label htmlFor="sameAs" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                    Permanent Address same as Current Address
                                </Label>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="p_address">Permanent Address</Label>
                                <Textarea
                                    id="p_address"
                                    {...register('permanent_address')}
                                    placeholder="Permanent address"
                                    disabled={sameAsCurrent || !isEditing}
                                />
                            </div>
                        </div>

                        {/* Family */}
                        <div>
                            <h3 className="text-sm font-semibold mb-3">Family</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Father */}
                                <div className="space-y-2">
                                    <Label htmlFor="father">Father's Name</Label>
                                    <Input id="father" {...register('father_name')} disabled={!isEditing} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="father_dob">Father's DOB</Label>
                                    <Input type="date" id="father_dob" {...register('father_dob')} disabled={!isEditing} />
                                </div>

                                {/* Mother */}
                                <div className="space-y-2">
                                    <Label htmlFor="mother">Mother's Name</Label>
                                    <Input id="mother" {...register('mother_name')} disabled={!isEditing} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="mother_dob">Mother's DOB</Label>
                                    <Input type="date" id="mother_dob" {...register('mother_dob')} disabled={!isEditing} />
                                </div>

                                {/* Spouse */}
                                <div className="space-y-2">
                                    <Label htmlFor="spouse">Spouse Name</Label>
                                    <Input id="spouse" {...register('spouse_name')} disabled={!isEditing} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="spouse_dob">Spouse DOB</Label>
                                    <Input type="date" id="spouse_dob" {...register('spouse_dob')} disabled={!isEditing} />
                                </div>

                                {/* Children */}
                                <div className="space-y-2 md:col-span-2">
                                    <Label htmlFor="children">Children's Name(s)</Label>
                                    <Input id="children" {...register('children_names')} placeholder="Comma separated names" disabled={!isEditing} />
                                </div>
                            </div>
                        </div>

                        {/* Emergency */}
                        <div>
                            <h3 className="text-sm font-semibold mb-3">Emergency Contact</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="ename">Contact Name</Label>
                                    <Input id="ename" {...register('emergency_contact_name')} disabled={!isEditing} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="ephone">Phone Number</Label>
                                    <Input id="ephone" {...register('emergency_contact_phone')} disabled={!isEditing} />
                                </div>
                            </div>
                        </div>
                    </fieldset>

                    {isEditing && (
                        <div className="flex space-x-2">
                            <Button type="submit" disabled={isLoading}>
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Save Changes
                            </Button>
                            <Button variant="ghost" onClick={toggleEdit} disabled={isLoading}>
                                Cancel
                            </Button>
                        </div>
                    )}
                </form>
            </CardContent>
        </Card >
    );
}
